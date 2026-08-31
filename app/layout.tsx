import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'NeuroSage | Safety-Aware Clinical AI Research',
    template: '%s | NeuroSage',
  },
  description:
    'An interactive research prototype for multimodal Alzheimer’s and Parkinson’s analysis, prediction safety assessment, and clinical reporting.',
  icons: { icon: '/favicon.svg' },
  openGraph: {
    title: 'NeuroSage',
    description: 'Explainable & Safety-Aware Clinical Prediction Platform',
    type: 'website',
    images: [
      {
        url: '/og.png',
        width: 1672,
        height: 941,
        alt: 'NeuroSage clinical AI research workflow and three-state prediction safety gate',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NeuroSage',
    description: 'Explainable & Safety-Aware Clinical Prediction Platform',
    images: ['/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
