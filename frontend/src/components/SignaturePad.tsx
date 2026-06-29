import { useRef, useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Eraser, Check, X } from 'lucide-react'

interface SignaturePadProps {
  onSave: (signatureDataUrl: string) => void
  onCancel: () => void
  width?: number
  height?: number
}

export default function SignaturePad({
  onSave,
  onCancel,
  width = 500,
  height = 200,
}: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null)
  const isDrawingRef = useRef(false)
  const [isEmpty, setIsEmpty] = useState(true)

  // Initialize the canvas: high-DPI backing store, white background, stroke style.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx.scale(dpr, dpr)
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'
    ctx.strokeStyle = '#1e3a5f'
    ctx.lineWidth = 2.5
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctxRef.current = ctx
    setIsEmpty(true)
  }, [width, height])

  const getPos = (e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }
  }

  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault()
    const ctx = ctxRef.current
    const canvas = canvasRef.current
    if (!ctx || !canvas) return
    isDrawingRef.current = true
    if (isEmpty) setIsEmpty(false)
    canvas.setPointerCapture(e.pointerId)
    const { x, y } = getPos(e)
    ctx.beginPath()
    ctx.moveTo(x, y)
  }

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDrawingRef.current) return
    const ctx = ctxRef.current
    if (!ctx) return
    const { x, y } = getPos(e)
    ctx.lineTo(x, y)
    ctx.stroke()
  }

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!isDrawingRef.current) return
    isDrawingRef.current = false
    canvasRef.current?.releasePointerCapture(e.pointerId)
  }

  const handleClear = () => {
    const ctx = ctxRef.current
    if (!ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    setIsEmpty(true)
  }

  const handleSave = () => {
    if (isEmpty) return
    const canvas = canvasRef.current
    if (!canvas) return
    onSave(canvas.toDataURL('image/png'))
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative" style={{ width, height }}>
        <canvas
          ref={canvasRef}
          className="rounded-md border-2 border-gray-300 bg-white"
          style={{ touchAction: 'none' }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          onPointerCancel={handlePointerUp}
        />
        {isEmpty && (
          <span className="pointer-events-none absolute inset-0 flex select-none items-center justify-center text-2xl text-gray-300">
            Firma aquí
          </span>
        )}
      </div>

      <div className="flex w-full justify-center gap-2">
        <Button type="button" variant="outline" onClick={handleClear}>
          <Eraser className="mr-2 h-4 w-4" />
          Limpiar
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          <X className="mr-2 h-4 w-4" />
          Cancelar
        </Button>
        <Button type="button" onClick={handleSave} disabled={isEmpty}>
          <Check className="mr-2 h-4 w-4" />
          Guardar firma
        </Button>
      </div>
    </div>
  )
}