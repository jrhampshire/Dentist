import { useState, useMemo } from 'react'
import { Image, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { PatientImage, ImageType } from '@/types/dental-records'
import { IMAGE_TYPE_LABELS } from '@/types/dental-records'

const IMAGE_TYPES: ImageType[] = ['photo', 'xray_periapical', 'xray_panoramic', 'xray_cephalometric', 'document', 'other']

interface ImageGalleryProps {
  images: PatientImage[]
  onImageClick: (image: PatientImage) => void
  loading?: boolean
}

export function ImageGallery({ images, onImageClick, loading = false }: ImageGalleryProps) {
  const [filterType, setFilterType] = useState<ImageType | null>(null)
  const [filterTooth, setFilterTooth] = useState<string>('')

  const uniqueTeeth = useMemo(() => {
    const teeth = new Set<number>()
    images.forEach((img) => {
      if (img.tooth_fdi != null) teeth.add(img.tooth_fdi)
    })
    return Array.from(teeth).sort((a, b) => a - b)
  }, [images])

  const filteredImages = useMemo(() => {
    return images.filter((img) => {
      if (filterType && img.image_type !== filterType) return false
      if (filterTooth && img.tooth_fdi?.toString() !== filterTooth) return false
      return true
    })
  }, [images, filterType, filterTooth])

  // ── Loading skeleton ──
  if (loading) {
    return (
      <div className="space-y-4">
        {/* Filter skeleton */}
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-6 w-24 animate-pulse rounded-full bg-muted" />
          ))}
        </div>
        {/* Grid skeleton */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="aspect-square animate-pulse rounded-lg bg-muted" />
              <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Empty state ──
  if (images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border bg-muted/20 py-16 text-muted-foreground">
        <Image className="mb-3 h-12 w-12 opacity-40" />
        <p className="text-lg font-medium">No hay imágenes registradas</p>
        <p className="mt-1 text-sm">Usa el formulario superior para subir la primera imagen.</p>
      </div>
    )
  }

  // ── Format utils ──
  const formatDate = (dateStr: string): string => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('es-MX', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="space-y-3">
        {/* Type filter chips */}
        <div className="flex flex-wrap gap-1.5">
          <Badge
            variant={filterType === null ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => setFilterType(null)}
          >
            Todas
          </Badge>
          {IMAGE_TYPES.map((type) => {
            const count = images.filter((img) => img.image_type === type).length
            if (count === 0) return null
            return (
              <Badge
                key={type}
                variant={filterType === type ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setFilterType(filterType === type ? null : type)}
              >
                {IMAGE_TYPE_LABELS[type]}
                <span className="ml-1 text-xs opacity-60">({count})</span>
              </Badge>
            )
          })}
        </div>

        {/* Tooth FDI filter */}
        {uniqueTeeth.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Diente:</span>
            <select
              value={filterTooth}
              onChange={(e) => setFilterTooth(e.target.value)}
              className="rounded-md border border-input bg-background px-2 py-1 text-xs"
            >
              <option value="">Todos</option>
              {uniqueTeeth.map((tooth) => (
                <option key={tooth} value={tooth.toString()}>
                  FDI {tooth}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Filtered empty state */}
      {filteredImages.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border bg-muted/10 py-12 text-muted-foreground">
          <Search className="mb-2 h-8 w-8 opacity-40" />
          <p>No hay imágenes con los filtros seleccionados.</p>
          <ButtonClear onClick={() => { setFilterType(null); setFilterTooth('') }} />
        </div>
      ) : (
        /* Grid */
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4">
          {filteredImages.map((image) => (
            <button
              key={image.id}
              type="button"
              onClick={() => onImageClick(image)}
              className="group relative flex flex-col overflow-hidden rounded-lg border bg-card text-left shadow-sm transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              {/* Thumbnail */}
              <div className="aspect-square relative bg-muted">
                {image.thumbnail_url ? (
                  <img
                    src={image.thumbnail_url}
                    alt={image.description || IMAGE_TYPE_LABELS[image.image_type]}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                    <Image className="h-8 w-8 opacity-40" />
                  </div>
                )}

                {/* Type badge overlay */}
                <div className="absolute left-1.5 top-1.5">
                  <Badge variant="secondary" className="text-[10px] shadow-sm">
                    {IMAGE_TYPE_LABELS[image.image_type]}
                  </Badge>
                </div>

                {/* Hover overlay */}
                <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/10">
                  <span className="rounded-full bg-background/90 px-3 py-1 text-xs font-medium opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
                    Ver
                  </span>
                </div>
              </div>

              {/* Info footer */}
              <div className="flex items-center justify-between gap-1 p-2">
                <span className="truncate text-xs text-muted-foreground">
                  {image.tooth_fdi != null ? `FDI ${image.tooth_fdi}` : IMAGE_TYPE_LABELS[image.image_type]}
                </span>
                <span className="shrink-0 text-[10px] text-muted-foreground">
                  {formatDate(image.uploaded_at)}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ButtonClear({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-2 text-sm text-primary hover:underline"
    >
      Limpiar filtros
    </button>
  )
}
