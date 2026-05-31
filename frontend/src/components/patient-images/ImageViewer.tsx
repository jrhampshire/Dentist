import { useCallback, useEffect, useState } from 'react'
import { X, ChevronLeft, ChevronRight, Trash2, ZoomIn, ZoomOut } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { PatientImage } from '@/types/dental-records'
import { IMAGE_TYPE_LABELS } from '@/types/dental-records'

interface ImageViewerProps {
  open: boolean
  onClose: () => void
  image: PatientImage | null
  onPrev?: () => void
  onNext?: () => void
  hasPrev?: boolean
  hasNext?: boolean
  onDelete?: (id: string) => void
}

export function ImageViewer({
  open,
  onClose,
  image,
  onPrev,
  onNext,
  hasPrev = false,
  hasNext = false,
  onDelete,
}: ImageViewerProps) {
  const [zoomed, setZoomed] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [imageError, setImageError] = useState(false)

  // Reset state when image changes
  useEffect(() => {
    setZoomed(false)
    setDeleteConfirm(false)
    setImageError(false)
  }, [image?.id])

  // Keyboard navigation
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && hasPrev && onPrev) {
        e.preventDefault()
        onPrev()
      } else if (e.key === 'ArrowRight' && hasNext && onNext) {
        e.preventDefault()
        onNext()
      } else if (e.key === 'Escape') {
        // Dialog handles Escape by default, but we intercept if zoomed
        if (zoomed) {
          e.preventDefault()
          setZoomed(false)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, hasPrev, hasNext, onPrev, onNext, zoomed])

  const handleDelete = useCallback(() => {
    if (!image || !onDelete) return
    if (!deleteConfirm) {
      setDeleteConfirm(true)
      return
    }
    onDelete(image.id)
  }, [image, onDelete, deleteConfirm])

  const formatDate = (dateStr: string): string => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('es-MX', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatFileSize = (bytes: number | null): string => {
    if (bytes == null) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  if (!image) return null

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent
        className="flex max-h-[90vh] max-w-[90vw] flex-col gap-0 p-0 sm:flex-row"
        onPointerDownOutside={(e) => {
          // Prevent closing when clicking outside while zoomed
          if (zoomed) e.preventDefault()
        }}
      >
        {/* Image area */}
        <div
          className="relative flex flex-1 items-center justify-center overflow-hidden bg-black/95"
          style={{ minHeight: '50vh' }}
        >
          {/* Close button (top-right corner of the image area) */}
          <button
            onClick={onClose}
            className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-background/20 text-white backdrop-blur-sm transition-colors hover:bg-background/40"
          >
            <X className="h-4 w-4" />
          </button>

          {/* Zoom toggle */}
          <button
            onClick={() => setZoomed(!zoomed)}
            className="absolute right-3 top-14 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-background/20 text-white backdrop-blur-sm transition-colors hover:bg-background/40"
          >
            {zoomed ? <ZoomOut className="h-4 w-4" /> : <ZoomIn className="h-4 w-4" />}
          </button>

          {/* Navigation arrows */}
          {hasPrev && onPrev && (
            <button
              onClick={onPrev}
              className="absolute left-3 top-1/2 z-10 -translate-y-1/2 flex h-10 w-10 items-center justify-center rounded-full bg-background/20 text-white backdrop-blur-sm transition-colors hover:bg-background/40"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
          )}
          {hasNext && onNext && (
            <button
              onClick={onNext}
              className="absolute right-3 top-1/2 z-10 -translate-y-1/2 flex h-10 w-10 items-center justify-center rounded-full bg-background/20 text-white backdrop-blur-sm transition-colors hover:bg-background/40"
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          )}

          {/* Image */}
          {imageError ? (
            <div className="flex flex-col items-center gap-2 text-white/60">
              <X className="h-12 w-12" />
              <p className="text-sm">No se pudo cargar la imagen</p>
            </div>
          ) : (
            <img
              src={image.image_url || ''}
              alt={image.description || IMAGE_TYPE_LABELS[image.image_type]}
              onError={() => setImageError(true)}
              className={`
                max-h-full max-w-full object-contain transition-transform duration-200
                ${zoomed ? 'cursor-zoom-out scale-150' : 'cursor-zoom-in'}
              `}
              onClick={() => setZoomed(!zoomed)}
            />
          )}
        </div>

        {/* Metadata panel */}
        <div className="flex w-full shrink-0 flex-col border-t bg-card sm:w-72 sm:border-l sm:border-t-0">
          <DialogHeader className="px-4 pt-4">
            <DialogTitle className="text-base">
              {IMAGE_TYPE_LABELS[image.image_type]}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 pb-4 pt-1">
            {/* Type badge */}
            <div>
              <Badge variant="secondary">{IMAGE_TYPE_LABELS[image.image_type]}</Badge>
            </div>

            {/* Tooth FDI */}
            {image.tooth_fdi != null && (
              <MetaRow label="Diente" value={`FDI ${image.tooth_fdi}`} />
            )}

            {/* Description */}
            {image.description && (
              <MetaRow label="Descripción" value={image.description} />
            )}

            {/* File info */}
            <MetaRow label="Tamaño" value={formatFileSize(image.file_size)} />
            <MetaRow label="Tipo de archivo" value={image.content_type || '—'} />

            {/* Uploaded by */}
            {image.uploaded_by_name && (
              <MetaRow label="Subido por" value={image.uploaded_by_name} />
            )}

            {/* Date */}
            <MetaRow label="Fecha" value={formatDate(image.uploaded_at)} />
          </div>

          {/* Delete button */}
          {onDelete && (
            <div className="border-t px-4 pb-4 pt-3">
              {deleteConfirm ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">¿Eliminar esta imagen permanentemente?</p>
                  <div className="flex gap-2">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleDelete}
                    >
                      <Trash2 className="mr-1 h-3 w-3" />
                      Sí, eliminar
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirm(false)}
                    >
                      Cancelar
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-destructive hover:text-destructive"
                  onClick={handleDelete}
                >
                  <Trash2 className="mr-1 h-3 w-3" />
                  Eliminar imagen
                </Button>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm break-words">{value}</dd>
    </div>
  )
}
