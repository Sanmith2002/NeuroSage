"""NeuroSage AD co-pathology service (IT23174276). Research prototype — not for clinical use."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import ValidationError

from . import clinical
from .config import VERSION, configure_threads, get_settings
from .features import engineer, to_frame
from .form_spec import display_name, form_spec
from .jobs import JobStore
from .registry import Registry
from .schema_output import DISCLAIMER, build_document
from .schemas import AssessRequest, ClinicalRequest, Health, MriFields, MriQC, MriResult

configure_threads()
log = logging.getLogger('ad-service')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

MAX_UPLOAD_BYTES = 600 * 1024 * 1024
DEMO_ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    reg = Registry(settings)
    app.state.registry, app.state.load_error = reg, None
    t0 = time.perf_counter()
    try:
        await asyncio.to_thread(reg.load)
    except Exception as e:      # keep serving /health so the failure is visible
        log.exception('model loading failed')
        app.state.load_error = str(e)
    log.info('startup finished in %.1fs', time.perf_counter() - t0)
    from .mri.render import ArtifactStore
    app.state.artifacts = ArtifactStore(settings.artifact_ttl_s)
    app.state.mri_jobs = JobStore(settings.artifact_ttl_s)
    app.state.mri_slot = threading.Semaphore(1)     # one CPU-heavy MRI pipeline at a time
    yield


app = FastAPI(title='NeuroSage AD co-pathology service', version=VERSION, lifespan=lifespan,
              description='Research prototype — not for clinical use.')
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list, allow_credentials=False,
                   allow_methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type', 'X-API-Key'])


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    key = get_settings().api_key
    if key and x_api_key != key:
        raise HTTPException(401, 'invalid or missing X-API-Key')


def registry(request: Request) -> Registry:
    if request.app.state.load_error:
        raise HTTPException(503, f'models not loaded: {request.app.state.load_error}')
    return request.app.state.registry


def _clean(x):
    """JSON-safe: NaN/inf → null, numpy scalars → python."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


# ------------------------------------------------------------------ meta
@app.get('/health', response_model=Health)
def health(request: Request):
    reg: Registry = request.app.state.registry
    status = 'ok' if not request.app.state.load_error else 'degraded'
    loaded = reg.summary()
    if request.app.state.load_error:
        loaded['error'] = request.app.state.load_error
    return Health(status=status, models_loaded=loaded, version=VERSION)


@app.get('/v1/models', dependencies=[Depends(require_key)])
def models(reg: Registry = Depends(registry)):
    from .mri.preprocess import PREPROC_SPEC
    thresholds = {k: {L: float(v) for L, v in b['thresholds'].items()} for k, b in reg.nacc.items()}
    adni = {k: {'kind': b['kind'], 'arch': b.get('arch'), 'threshold': float(b['threshold']),
                'tab_features': list(b['tab_features']), 'n_folds': len(b['folds'])} for k, b in reg.adni.items()}
    return _clean({
        'model_card': reg.model_card,
        'registry': reg.summary(),
        'active_nacc_model': reg.active_nacc(),
        'nacc_thresholds': thresholds,
        'adni': adni,
        'reported_performance': clinical.REPORTED,
        'explanation_stability': {L: {'spearman': s, 'jaccard_top10': j} for L, (s, j) in clinical.STABILITY.items()},
        'openset_caveat': 'Open-set (FTLD/ALS vs target) detection AUROC ≈ 0.49–0.53: experimental, never reassuring.',
        'data_sources': ['NACC (National Alzheimer’s Coordinating Center) UDS + neuropathology',
                         'ADNI (Alzheimer’s Disease Neuroimaging Initiative) T1 MRI + CSF'],
        'dua_notice': 'Models were trained on NACC and ADNI data under their data-use agreements. '
                      'No participant data is served by this API.',
        'preprocessing': PREPROC_SPEC,
        'disclaimer': DISCLAIMER,
    })


@app.get('/v1/form-spec', dependencies=[Depends(require_key)])
def get_form_spec():
    return form_spec()


# ------------------------------------------------------------------ clinical
@app.post('/v1/clinical/features', dependencies=[Depends(require_key)])
def clinical_features(req: ClinicalRequest, reg: Registry = Depends(registry)):
    eng = engineer(req)
    bundle = reg.get_nacc(reg.active_nacc() if req.options.model == 'auto' else req.options.model)
    X, missing = to_frame(eng.features, list(bundle['features']))
    return _clean({
        'features': [{'name': c, 'display_name': display_name(c), 'value': X.iloc[0][c]} for c in X.columns],
        'not_produced': missing,
        'visits': eng.visits.assign(date=eng.visits.date.astype(str)).to_dict('records'),
        'harmonisation_log': eng.harmonisation_log,
        'warnings': eng.warnings,
    })


def _clinical_document(reg: Registry, req: ClinicalRequest, mri: MriResult | None = None) -> dict:
    eng = engineer(req)
    try:
        cr = clinical.predict(reg, eng, req.options.model, req.options.explain, get_settings().shap_cache_size)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e
    return _clean(build_document(reg, req, eng, cr, mri))


@app.post('/v1/clinical/predict', dependencies=[Depends(require_key)])
def clinical_predict(req: ClinicalRequest, reg: Registry = Depends(registry)):
    return _clinical_document(reg, req)


@app.post('/v1/assess', dependencies=[Depends(require_key)])
def assess(req: AssessRequest, reg: Registry = Depends(registry)):
    return _clinical_document(reg, req.clinical, req.mri_result)


# ------------------------------------------------------------------ MRI
def _finish_mri(request: Request, reg: Registry, x: np.ndarray, fields: MriFields, qc: dict | None,
                timings: dict, source: str, progress=lambda s, p: None) -> MriResult:
    from .mri import predict as mp
    from .mri import render

    progress('predict', 0.88)
    t0 = time.perf_counter()
    out = mp.predict_all(reg, x, fields)
    timings['predict'] = round(time.perf_counter() - t0, 2)
    store = request.app.state.artifacts
    if 'ad_clin' in reg.nets:
        progress('explain', 0.94)
        t1 = time.perf_counter()
        cam = mp.gradcam(reg, x, fields)
        out['gradcam_png'] = f'/v1/mri/artifacts/{store.put(render.gradcam_png(x, cam, out.get("p_ad_clin")))}.png'
        timings['explain'] = round(time.perf_counter() - t1, 2)
    out['qc_png'] = f'/v1/mri/artifacts/{store.put(render.qc_png(x, qc))}.png'
    return MriResult(**out, qc=MriQC(**qc) if qc else None, timings_s=timings, source=source)


def _sse(event: str, data) -> bytes:
    return f'event: {event}\ndata: {json.dumps(_clean(data))}\n\n'.encode()


async def _save_upload(reg: Registry, file: UploadFile, fields: str) -> tuple[Path, Path, MriFields]:
    """Validates the form and spools the scan into a fresh work dir, which the caller must delete."""
    if 'ad_clin' not in reg.adni:
        raise HTTPException(503, 'MRI models are not loaded on this deployment (LOAD_MRI=false)')
    try:
        mf = MriFields.model_validate_json(fields or '{}')
    except ValidationError as e:
        raise HTTPException(422, json.loads(e.json())) from e
    fname = Path(file.filename or 'scan.nii.gz').name.lower()
    suffix = '.nii.gz' if fname.endswith('.nii.gz') else Path(fname).suffix
    if suffix not in {'.nii', '.nii.gz', '.zip'}:
        raise HTTPException(422, 'upload a .nii, .nii.gz or .zip (DICOM series)')

    work = Path(tempfile.mkdtemp(prefix='adsvc-'))
    src = work / f'upload{suffix}'
    size = 0
    try:
        with src.open('wb') as fh:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, 'file too large')
                fh.write(chunk)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return work, src, mf


def _run_mri(request: Request, reg: Registry, work: Path, src: Path, mf: MriFields, emit) -> None:
    """Runs the whole MRI pipeline on a worker thread, reporting through emit('stage' | 'result' | 'error', data).
    Deletes `work` when done."""
    from .mri import preprocess
    settings = get_settings()
    slot = request.app.state.mri_slot
    try:
        if not slot.acquire(blocking=False):
            emit('stage', {'stage': 'queued', 'progress': 0.0})
            slot.acquire()
        try:
            t0 = time.perf_counter()
            pre = preprocess.run(src, work, settings.cache_dir,
                                 lambda s, p: emit('stage', {'stage': s, 'progress': p}), settings.hd_bet_device)
            res = _finish_mri(request, reg, pre.x, mf, pre.qc, pre.timings_s, 'upload',
                              lambda s, p: emit('stage', {'stage': s, 'progress': p}))
            res.timings_s['total'] = round(time.perf_counter() - t0, 2)
            emit('stage', {'stage': 'explain', 'progress': 1.0})
            emit('result', res.model_dump())
        finally:
            slot.release()
    except preprocess.PipelineError as e:
        emit('error', {'code': e.code, 'message': e.message})
    except Exception:
        log.exception('MRI pipeline failed')          # never logs file contents or patient fields
        emit('error', {'code': 'INTERNAL', 'message': 'MRI analysis failed on the server'})
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.post('/v1/mri/jobs', status_code=202, dependencies=[Depends(require_key)])
async def mri_job_start(request: Request, file: UploadFile = File(...), fields: str = Form('{}'),
                        reg: Registry = Depends(registry)):
    """Starts the MRI analysis in the background; poll GET /v1/mri/jobs/{id}. Unlike the /v1/mri/analyze stream,
    no request outlives a proxy timeout (Container Apps ends HTTP requests after 240 s; the pipeline takes longer)."""
    work, src, mf = await _save_upload(reg, file, fields)
    job = request.app.state.mri_jobs.create()

    def emit(event: str, data) -> None:
        if event == 'stage':
            job.update(status='running', stage=data['stage'], progress=data['progress'])
        elif event == 'result':
            job.update(status='done', result=_clean(data))
        elif event == 'error':
            job.update(status='error', error=data)

    threading.Thread(target=_run_mri, args=(request, reg, work, src, mf, emit), daemon=True,
                     name=f'mri-{job.id[:8]}').start()
    return job.view()


@app.get('/v1/mri/jobs/{job_id}', dependencies=[Depends(require_key)])
def mri_job_status(job_id: str, request: Request):
    job = request.app.state.mri_jobs.get(job_id)
    if job is None:
        raise HTTPException(404, 'MRI job not found: it expired, or the service restarted while it ran')
    return job.view()


@app.post('/v1/mri/analyze', dependencies=[Depends(require_key)])
async def mri_analyze(request: Request, file: UploadFile = File(...), fields: str = Form('{}'),
                      reg: Registry = Depends(registry)):
    work, src, mf = await _save_upload(reg, file, fields)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(event: str, data) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, (event, data))

    def worker() -> None:
        try:
            _run_mri(request, reg, work, src, mf, emit)
        finally:
            emit('__end__', None)

    async def stream():
        task = loop.run_in_executor(None, worker)
        try:
            while True:
                try:
                    event, data = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield b': keep-alive\n\n'
                    continue
                if event == '__end__':
                    break
                yield _sse(event, data)
        finally:
            await asyncio.shield(task)

    return StreamingResponse(stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.get('/v1/mri/artifacts/{token}.png')
def mri_artifact(token: str, request: Request):
    png = request.app.state.artifacts.get(token)
    if png is None:
        raise HTTPException(404, 'artifact expired or not found')
    return Response(png, media_type='image/png', headers={'Cache-Control': 'private, max-age=1800'})


def _demo_dir() -> Path | None:
    d = get_settings().demo_dir
    return d if d and d.is_dir() else None


@app.get('/v1/mri/demo-cases', dependencies=[Depends(require_key)])
def demo_cases():
    d = _demo_dir()
    if d is None:
        return {'cases': []}
    cases = []
    for npy in sorted(d.glob('*.npy')):
        meta_p = npy.with_suffix('.json')
        meta = json.loads(meta_p.read_text(encoding='utf-8')) if meta_p.exists() else {}
        cases.append({'id': npy.stem, 'description': meta.get('description', npy.stem),
                      'fields': meta.get('fields', {})})
    return {'cases': cases}


@app.post('/v1/mri/demo-cases/{case_id}/predict', dependencies=[Depends(require_key)])
def demo_predict(case_id: str, request: Request, fields: MriFields | None = None, reg: Registry = Depends(registry)):
    d = _demo_dir()
    if d is None or not DEMO_ID.match(case_id) or not (d / f'{case_id}.npy').exists():
        raise HTTPException(404, 'demo case not found')
    if 'ad_clin' not in reg.adni:
        raise HTTPException(503, 'MRI models are not loaded on this deployment (LOAD_MRI=false)')
    x = np.load(d / f'{case_id}.npy').astype(np.float32)
    if x.shape != (80, 96, 80):
        raise HTTPException(500, f'demo volume has shape {x.shape}, expected (80, 96, 80)')
    if fields is None:
        meta_p = d / f'{case_id}.json'
        meta = json.loads(meta_p.read_text(encoding='utf-8')) if meta_p.exists() else {}
        fields = MriFields(**meta.get('fields', {}))
    return _clean(_finish_mri(request, reg, x, fields, None, {}, 'demo').model_dump())


@app.exception_handler(FileNotFoundError)
async def missing_model(_request: Request, exc: FileNotFoundError):
    return JSONResponse({'detail': str(exc)}, status_code=400)
