import { useState } from 'react'
import {
  CONDITION_COLORS,
  type ToothState,
  type ToothCondition,
} from '@/types/dental-records'

// ── Tooth Definition ────────────────────────────────────────────────

interface ToothDef {
  fdi: number
  x: number
  y: number
  w: number
  h: number
  isPrimary: boolean
  labelOffsetY: number
}

type ArchName = 'maxillary' | 'mandibular'

interface ArchQuadrant {
  arch: ArchName
  teeth: ToothDef[]
}

// ── Permanent FDI ranges ──
const PERM_UR: number[] = [18, 17, 16, 15, 14, 13, 12, 11]
const PERM_UL: number[] = [21, 22, 23, 24, 25, 26, 27, 28]
const PERM_LR: number[] = [48, 47, 46, 45, 44, 43, 42, 41]
const PERM_LL: number[] = [31, 32, 33, 34, 35, 36, 37, 38]

// ── Primary FDI ranges ──
const PRIM_UR: number[] = [55, 54, 53, 52, 51]
const PRIM_UL: number[] = [61, 62, 63, 64, 65]
const PRIM_LR: number[] = [85, 84, 83, 82, 81]
const PRIM_LL: number[] = [71, 72, 73, 74, 75]

// ── Layout constants ──
const SVG_W = 800
const SVG_H = 500

const PERM_TOOTH_W = 30
const PERM_TOOTH_H = 42
const PRIM_TOOTH_W = 22
const PRIM_TOOTH_H = 32

const PERM_SPACING = 40   // center-to-center
const PRIM_SPACING = 32   // center-to-center

const Y_PERM_UPPER = 130
const Y_PERM_LOWER = 370
const Y_PRIM_UPPER = 210
const Y_PRIM_LOWER = 290

const CENTER_GAP = 60     // gap at x=400 between left/right quadrants
const CENTER_X = 400      // midline

// ── Build tooth definitions ──

function buildQuadrant(
  fdiList: number[],
  y: number,
  toothW: number,
  toothH: number,
  spacing: number,
  isPrimary: boolean,
  alignRight: boolean, // false = left quadrant (teeth left of center), true = right
  labelOffsetY: number
): ToothDef[] {
  return fdiList.map((fdi, i) => {
    let cx: number
    if (alignRight) {
      // Right quadrant: starts from center going right
      cx = CENTER_X + CENTER_GAP / 2 + i * spacing
    } else {
      // Left quadrant: starts from far left going toward center
      cx = CENTER_X - CENTER_GAP / 2 - (fdiList.length - 1 - i) * spacing
    }
    return { fdi, x: cx, y, w: toothW, h: toothH, isPrimary, labelOffsetY }
  })
}

function getAllTeeth(): { quadrants: ArchQuadrant[]; teeth: ToothDef[] } {
  const labelOff = 54 // how far below tooth center to render FDI label

  const quadrants: ArchQuadrant[] = [
    {
      arch: 'maxillary',
      teeth: [
        ...buildQuadrant(PERM_UR, Y_PERM_UPPER, PERM_TOOTH_W, PERM_TOOTH_H, PERM_SPACING, false, false, labelOff),
        ...buildQuadrant(PERM_UL, Y_PERM_UPPER, PERM_TOOTH_W, PERM_TOOTH_H, PERM_SPACING, false, true, labelOff),
      ],
    },
    {
      arch: 'maxillary',
      teeth: [
        ...buildQuadrant(PRIM_UR, Y_PRIM_UPPER, PRIM_TOOTH_W, PRIM_TOOTH_H, PRIM_SPACING, true, false, labelOff),
        ...buildQuadrant(PRIM_UL, Y_PRIM_UPPER, PRIM_TOOTH_W, PRIM_TOOTH_H, PRIM_SPACING, true, true, labelOff),
      ],
    },
    {
      arch: 'mandibular',
      teeth: [
        ...buildQuadrant(PRIM_LR, Y_PRIM_LOWER, PRIM_TOOTH_W, PRIM_TOOTH_H, PRIM_SPACING, true, false, labelOff),
        ...buildQuadrant(PRIM_LL, Y_PRIM_LOWER, PRIM_TOOTH_W, PRIM_TOOTH_H, PRIM_SPACING, true, true, labelOff),
      ],
    },
    {
      arch: 'mandibular',
      teeth: [
        ...buildQuadrant(PERM_LR, Y_PERM_LOWER, PERM_TOOTH_W, PERM_TOOTH_H, PERM_SPACING, false, false, labelOff),
        ...buildQuadrant(PERM_LL, Y_PERM_LOWER, PERM_TOOTH_W, PERM_TOOTH_H, PERM_SPACING, false, true, labelOff),
      ],
    },
  ]

  const allTeeth = quadrants.flatMap((q) => q.teeth)
  return { quadrants, teeth: allTeeth }
}

// ── Surface geometries (relative to tooth center) ──

interface SurfaceDef {
  id: string
  x: number
  y: number
  w: number
  h: number
}

function getSurfaces(tooth: ToothDef): SurfaceDef[] {
  const hw = tooth.w / 2
  const hh = tooth.h / 2
  const sideW = tooth.w * 0.25
  const midW = tooth.w * 0.50
  const sideH = tooth.h * 0.25
  const midH = tooth.h * 0.50

  if (tooth.isPrimary) {
    // 4 surfaces: mesial(left), distal(right), buccal(top), lingual(bottom)
    return [
      { id: 'mesial',  x: -hw,               y: -hh,               w: sideW, h: tooth.h },
      { id: 'distal',  x: -hw + midW + sideW, y: -hh,               w: sideW, h: tooth.h },
      { id: 'buccal',  x: -hw + sideW,         y: -hh,               w: midW,  h: sideH },
      { id: 'lingual', x: -hw + sideW,         y: -hh + midH + sideH, w: midW,  h: sideH },
    ]
  }
  // 5 surfaces: mesial, distal, buccal, lingual, occlusal(center)
  return [
    { id: 'mesial',   x: -hw,               y: -hh,               w: sideW, h: tooth.h },
    { id: 'distal',   x: -hw + midW + sideW, y: -hh,               w: sideW, h: tooth.h },
    { id: 'buccal',   x: -hw + sideW,         y: -hh,               w: midW,  h: sideH },
    { id: 'lingual',  x: -hw + sideW,         y: -hh + midH + sideH, w: midW,  h: sideH },
    { id: 'occlusal', x: -hw + sideW,         y: -hh + sideH,        w: midW,  h: midH  },
  ]
}

// ── Props & Component ──

interface OdontogramSVGProps {
  teeth: ToothState[]
  onSurfaceClick: (toothFdi: number, surface: string) => void
}

export function OdontogramSVG({ teeth, onSurfaceClick }: OdontogramSVGProps) {
  const [hovered, setHovered] = useState<{ fdi: number; surface: string } | null>(null)
  const { quadrants } = getAllTeeth()

  // Build lookup: fdi → ToothState
  const toothMap = new Map<number, ToothState>()
  for (const t of teeth) {
    toothMap.set(t.tooth_fdi, t)
  }

  // Get condition color for a tooth surface
  const getCondition = (tooth: ToothDef, surfaceId: string): ToothCondition => {
    const ts = toothMap.get(tooth.fdi)
    if (!ts) return 'healthy'
    const surf = ts.surfaces?.find((s) => s.surface === surfaceId)
    return (surf?.condition as ToothCondition) || ts.condition || 'healthy'
  }

  const defaultColor = '#e5e7eb' // gray-200 for unclicked/healthy

  // Section labels
  const archLabels = [
    { text: 'Maxilar Superior', x: SVG_W / 2, y: 30 },
    { text: 'Maxilar Superior (Primarios)', x: SVG_W / 2, y: Y_PRIM_UPPER - 30 },
    { text: 'Mandibular (Primarios)', x: SVG_W / 2, y: Y_PRIM_LOWER - 30 },
    { text: 'Mandibular Inferior', x: SVG_W / 2, y: Y_PERM_LOWER - 30 },
  ]

  return (
    <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full max-w-3xl mx-auto" role="img" aria-label="Odontograma dental">
      {/* Background */}
      <rect x="0" y="0" width={SVG_W} height={SVG_H} fill="#f9fafb" rx="8" />

      {/* Section labels */}
      {archLabels.map((l) => (
        <text
          key={l.text}
          x={l.x}
          y={l.y}
          textAnchor="middle"
          className="fill-gray-400 text-[10px]"
          fontFamily="system-ui, sans-serif"
        >
          {l.text}
        </text>
      ))}

      {/* Center gap divider */}
      <line x1={CENTER_X} y1="40" x2={CENTER_X} y2={SVG_H - 20} stroke="#e5e7eb" strokeWidth="1" strokeDasharray="4 4" />

      {/* Quadrant arcs (visual separators) */}
      {quadrants.map((quad) =>
        quad.teeth.map((tooth) => {
          const surfaces = getSurfaces(tooth)
          const hoveredHere = hovered !== null && hovered.fdi === tooth.fdi

          return (
            <g key={tooth.fdi} transform={`translate(${tooth.x}, ${tooth.y})`}>
              {/* Tooth outline */}
              <rect
                x={-tooth.w / 2}
                y={-tooth.h / 2}
                width={tooth.w}
                height={tooth.h}
                fill="none"
                stroke={tooth.isPrimary ? '#d1d5db' : '#9ca3af'}
                strokeWidth={tooth.isPrimary ? 0.8 : 1.2}
                rx={3}
                ry={3}
              />

              {/* Surface polygons */}
              {surfaces.map((surf) => {
                const condition = getCondition(tooth, surf.id)
                const color = CONDITION_COLORS[condition] || defaultColor
                const isHovered =
                  hoveredHere && hovered.surface === surf.id

                return (
                  <rect
                    key={surf.id}
                    x={surf.x}
                    y={surf.y}
                    width={surf.w}
                    height={surf.h}
                    fill={isHovered ? lighten(color) : color}
                    stroke={isHovered ? '#374151' : '#e5e7eb'}
                    strokeWidth={0.5}
                    rx={1}
                    style={{ cursor: 'pointer' }}
                    role="button"
                    aria-label={`Diente ${tooth.fdi}, superficie ${surf.id}: ${condition}`}
                    onClick={() => onSurfaceClick(tooth.fdi, surf.id)}
                    onMouseEnter={() => setHovered({ fdi: tooth.fdi, surface: surf.id })}
                    onMouseLeave={() => setHovered(null)}
                  />
                )
              })}

              {/* FDI label */}
              <text
                x="0"
                y={tooth.h / 2 + 14}
                textAnchor="middle"
                className="fill-gray-600 text-[9px] font-semibold"
                fontFamily="system-ui, sans-serif"
              >
                {tooth.fdi}
              </text>
            </g>
          )
        })
      )}
    </svg>
  )
}

// ── Utility: lighten a hex color by 15% ──
function lighten(hex: string): string {
  if (hex === 'transparent') return '#d1d5db'
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const f = (c: number) => Math.min(255, Math.round(c + (255 - c) * 0.15))
  return `#${f(r).toString(16).padStart(2, '0')}${f(g).toString(16).padStart(2, '0')}${f(b).toString(16).padStart(2, '0')}`
}
