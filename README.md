# NeuroSage

Interactive frontend prototype for the NeuroSage clinical AI assessment workflow.

## Prerequisites

- [Node.js](https://nodejs.org/) 22.13.0 or newer
- npm (included with Node.js)

## Run locally

Clone the repository and enter the project directory:

```bash
git clone https://github.com/Sanmith2002/NeuroSage.git
cd NeuroSage
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed in the terminal, normally [http://localhost:3000](http://localhost:3000).

## Production build

Create an optimized build:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run start
```

## Quality checks

Run the linter:

```bash
npm run lint
```

Format the source code:

```bash
npm run format
```

## Main routes

- `/` - case dashboard
- `/assessment/new` - create a new assessment
- `/workflow` - workflow overview
- `/assessment/:caseId/:stage` - patient, harmonization, predictions, safety, and report stages

This repository is a frontend demonstration and uses static research data. It is not intended for clinical use.
