/**
 * Hand-drawn style illustration components for feature/scenario cards.
 * Each illustration combines multiple elements with hand-drawn aesthetic
 * (organic shapes, decorative dots, slight imperfections).
 */
import type { CSSProperties } from 'react'

interface IllustrationProps {
  size?: number
  className?: string
  style?: CSSProperties
}

const baseProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

// Magnifier with risk highlights
export const RiskAnalysisIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <rect x="10" y="14" width="32" height="40" rx="3"/>
    <line x1="16" y1="22" x2="36" y2="22"/>
    <line x1="16" y1="28" x2="32" y2="28"/>
    <line x1="16" y1="34" x2="36" y2="34"/>
    <circle cx="42" cy="42" r="10" strokeWidth="2.4"/>
    <line x1="49" y1="49" x2="56" y2="56" strokeWidth="2.4"/>
    <circle cx="42" cy="42" r="2" fill="currentColor"/>
    <path d="M22 44 l3 3" strokeDasharray="2 2"/>
  </svg>
)

// Globe / scales for jurisdictions
export const JurisdictionIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <circle cx="32" cy="28" r="18"/>
    <ellipse cx="32" cy="28" rx="9" ry="18"/>
    <line x1="14" y1="28" x2="50" y2="28"/>
    <path d="M32 46 v8 M22 54 h20"/>
    <circle cx="20" cy="20" r="2" fill="currentColor" opacity="0.6"/>
    <circle cx="44" cy="34" r="2" fill="currentColor" opacity="0.6"/>
  </svg>
)

// Speech bubble with quote
export const NegotiationIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M10 14 H46 a4 4 0 0 1 4 4 v18 a4 4 0 0 1 -4 4 H30 l-8 8 v-8 H14 a4 4 0 0 1 -4 -4 V18 a4 4 0 0 1 4 -4 z"/>
    <text x="20" y="32" fontSize="14" fontFamily="serif" fontStyle="italic" fill="currentColor" stroke="none">"</text>
    <text x="34" y="32" fontSize="14" fontFamily="serif" fontStyle="italic" fill="currentColor" stroke="none">"</text>
    <circle cx="52" cy="48" r="6" opacity="0.5"/>
    <path d="M50 48 l1.5 1.5 L55 46" strokeWidth="1.5"/>
  </svg>
)

// Document with simple language icon
export const PlainLanguageIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M14 10 H38 l10 10 V52 a3 3 0 0 1 -3 3 H14 a3 3 0 0 1 -3 -3 V13 a3 3 0 0 1 3 -3 z"/>
    <path d="M38 10 V20 H48"/>
    <line x1="18" y1="30" x2="42" y2="30"/>
    <line x1="18" y1="36" x2="38" y2="36"/>
    <line x1="18" y1="42" x2="34" y2="42"/>
    <circle cx="48" cy="50" r="5" fill="currentColor" opacity="0.15"/>
    <text x="44" y="53" fontSize="8" fontFamily="serif" fill="currentColor" stroke="none">A</text>
  </svg>
)

// Lightning + clock for speed
export const SpeedIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <circle cx="24" cy="32" r="16"/>
    <line x1="24" y1="22" x2="24" y2="32"/>
    <line x1="24" y1="32" x2="32" y2="36"/>
    <path d="M44 14 L36 28 H44 L40 46 L52 28 H44 Z" fill="currentColor" fillOpacity="0.25"/>
    <circle cx="24" cy="14" r="1.5" fill="currentColor"/>
    <circle cx="24" cy="50" r="1.5" fill="currentColor"/>
    <circle cx="8" cy="32" r="1.5" fill="currentColor"/>
    <circle cx="40" cy="32" r="1.5" fill="currentColor"/>
  </svg>
)

// Shield with lock for privacy
export const PrivacyIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M32 6 L52 14 V32 c0 12 -8 22 -20 26 -12 -4 -20 -14 -20 -26 V14 z"/>
    <rect x="24" y="28" width="16" height="14" rx="2"/>
    <path d="M28 28 V22 a4 4 0 0 1 8 0 V28"/>
    <circle cx="32" cy="35" r="2" fill="currentColor"/>
    <path d="M32 35 v3"/>
  </svg>
)

// Two documents diff
export const CompareIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <rect x="6" y="10" width="22" height="32" rx="2"/>
    <rect x="36" y="22" width="22" height="32" rx="2"/>
    <line x1="10" y1="18" x2="24" y2="18"/>
    <line x1="10" y1="24" x2="22" y2="24"/>
    <line x1="10" y1="30" x2="24" y2="30"/>
    <line x1="40" y1="30" x2="54" y2="30"/>
    <line x1="40" y1="36" x2="52" y2="36"/>
    <line x1="40" y1="42" x2="54" y2="42"/>
    <path d="M28 32 q4 -8 8 0" strokeDasharray="2 2"/>
  </svg>
)

// Warning triangle with text
export const TrapIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M32 8 L56 50 H8 z"/>
    <line x1="32" y1="22" x2="32" y2="36"/>
    <circle cx="32" cy="42" r="2" fill="currentColor"/>
    <circle cx="14" cy="14" r="2" fill="currentColor" opacity="0.5"/>
    <circle cx="52" cy="20" r="2" fill="currentColor" opacity="0.5"/>
    <path d="M44 8 q4 4 8 0" strokeWidth="1.4"/>
  </svg>
)

// Bar chart
export const BarChartIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <line x1="8" y1="54" x2="56" y2="54"/>
    <rect x="14" y="36" width="8" height="18" rx="1"/>
    <rect x="28" y="22" width="8" height="32" rx="1" fill="currentColor" fillOpacity="0.2"/>
    <rect x="42" y="30" width="8" height="24" rx="1"/>
    <path d="M14 28 l14 -10 l14 6" strokeDasharray="2 2"/>
    <circle cx="14" cy="28" r="2" fill="currentColor"/>
    <circle cx="28" cy="18" r="2" fill="currentColor"/>
    <circle cx="42" cy="24" r="2" fill="currentColor"/>
  </svg>
)

// Side by side layout
export const LayoutIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <rect x="6" y="14" width="24" height="36" rx="2"/>
    <rect x="34" y="14" width="24" height="36" rx="2"/>
    <line x1="10" y1="22" x2="26" y2="22"/>
    <line x1="10" y1="28" x2="22" y2="28"/>
    <line x1="38" y1="22" x2="54" y2="22"/>
    <line x1="38" y1="28" x2="50" y2="28"/>
    <line x1="38" y1="34" x2="54" y2="34"/>
    <circle cx="32" cy="32" r="3" fill="currentColor" opacity="0.3"/>
  </svg>
)

// Briefcase
export const BriefcaseIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <rect x="8" y="20" width="48" height="32" rx="3"/>
    <path d="M22 20 V14 a3 3 0 0 1 3 -3 h14 a3 3 0 0 1 3 3 v6"/>
    <line x1="8" y1="34" x2="56" y2="34"/>
    <rect x="28" y="30" width="8" height="6" rx="1" fill="currentColor" fillOpacity="0.15"/>
  </svg>
)

// People
export const PeopleIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <circle cx="22" cy="22" r="8"/>
    <path d="M8 50 c0 -8 6 -14 14 -14 s14 6 14 14"/>
    <circle cx="44" cy="26" r="6"/>
    <path d="M36 52 c0 -6 6 -10 12 -10 s8 4 8 10" />
  </svg>
)

// Signature on document
export const SignatureIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M14 10 H38 l10 10 V52 a3 3 0 0 1 -3 3 H14 a3 3 0 0 1 -3 -3 V13 a3 3 0 0 1 3 -3 z"/>
    <path d="M38 10 V20 H48"/>
    <line x1="18" y1="30" x2="40" y2="30"/>
    <path d="M18 40 q3 -4 6 0 t6 0 t6 0" strokeWidth="2.2"/>
    <line x1="18" y1="48" x2="36" y2="48" strokeDasharray="2 2"/>
  </svg>
)

// Code brackets
export const CodeIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <rect x="6" y="14" width="52" height="36" rx="3"/>
    <line x1="6" y1="22" x2="58" y2="22"/>
    <circle cx="12" cy="18" r="1.5" fill="currentColor"/>
    <circle cx="17" cy="18" r="1.5" fill="currentColor"/>
    <circle cx="22" cy="18" r="1.5" fill="currentColor"/>
    <path d="M18 32 l-6 6 l6 6" strokeWidth="2.2"/>
    <path d="M46 32 l6 6 l-6 6" strokeWidth="2.2"/>
    <line x1="28" y1="42" x2="36" y2="32" strokeWidth="2"/>
  </svg>
)

// House with key
export const HouseIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M8 30 L32 10 L56 30 V52 a2 2 0 0 1 -2 2 H10 a2 2 0 0 1 -2 -2 z"/>
    <rect x="26" y="38" width="12" height="16" rx="1"/>
    <circle cx="34" cy="46" r="1.5" fill="currentColor"/>
    <line x1="14" y1="32" x2="14" y2="40"/>
    <line x1="50" y1="32" x2="50" y2="40"/>
  </svg>
)

// Building (investment)
export const BuildingIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <rect x="14" y="10" width="36" height="46" rx="2"/>
    <rect x="20" y="18" width="6" height="6" rx="0.5"/>
    <rect x="29" y="18" width="6" height="6" rx="0.5"/>
    <rect x="38" y="18" width="6" height="6" rx="0.5"/>
    <rect x="20" y="28" width="6" height="6" rx="0.5"/>
    <rect x="29" y="28" width="6" height="6" rx="0.5" fill="currentColor" fillOpacity="0.15"/>
    <rect x="38" y="28" width="6" height="6" rx="0.5"/>
    <rect x="28" y="42" width="8" height="14" rx="0.5"/>
    <path d="M32 6 L34 10 H30 z" fill="currentColor"/>
  </svg>
)

// Upload cloud
export const UploadIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M16 42 a10 10 0 0 1 4 -19 a14 14 0 0 1 27 4 a8 8 0 0 1 1 16 z"/>
    <path d="M32 30 V52" strokeWidth="2.4"/>
    <path d="M24 38 L32 30 L40 38" strokeWidth="2.4"/>
  </svg>
)

// Brain
export const BrainIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M32 12 c-8 0 -14 6 -14 14 c0 4 2 7 4 9 c-2 2 -3 4 -3 7 c0 6 4 10 10 10 c1 3 4 4 7 3"/>
    <path d="M32 12 c8 0 14 6 14 14 c0 4 -2 7 -4 9 c2 2 3 4 3 7 c0 6 -4 10 -10 10 c-1 3 -4 4 -7 3"/>
    <line x1="32" y1="12" x2="32" y2="58"/>
    <circle cx="24" cy="24" r="1.5" fill="currentColor"/>
    <circle cx="40" cy="32" r="1.5" fill="currentColor"/>
    <circle cx="26" cy="44" r="1.5" fill="currentColor"/>
  </svg>
)

// Check mark on document
export const ReportIllustration = ({ size = 48, className, style }: IllustrationProps) => (
  <svg width={size} height={size} viewBox="0 0 64 64" {...baseProps} className={className} style={style}>
    <path d="M14 10 H38 l10 10 V52 a3 3 0 0 1 -3 3 H14 a3 3 0 0 1 -3 -3 V13 a3 3 0 0 1 3 -3 z"/>
    <path d="M38 10 V20 H48"/>
    <line x1="18" y1="30" x2="42" y2="30"/>
    <line x1="18" y1="36" x2="38" y2="36"/>
    <circle cx="42" cy="46" r="8" strokeWidth="2.2"/>
    <path d="M38 46 l3 3 l5 -6" strokeWidth="2.2"/>
  </svg>
)
