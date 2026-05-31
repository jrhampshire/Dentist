import { useState, useCallback } from 'react'
import { Camera, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePatientImages, useCreatePatientImage, useDeletePatientImage } from '@/hooks/usePatientImages'
import { ImageUploader } from './ImageUploader'
import { ImageGallery } from './ImageGallery'
import { ImageViewer } from './ImageViewer'
import type { PatientImage } from '@/types/dental-records'

interface PatientImagesTabProps {
  patientId: string
}

export function PatientImagesTab({ patientId }: PatientImagesTabProps) {
  const [showUploader, setShowUploader] = useState(false)
  const [viewerOpen, setViewerOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState<number>(-1)

  const { data: images = [], isLoading, error } = usePatientImages(patientId)
  const createImage = useCreatePatientImage()
  const deleteImage = useDeletePatientImage()

  // ── Upload handler ──

  const handleUpload = useCallback(
    async (formData: FormData) => {
      try {
        await createImage.mutateAsync({
          patientId,
          formData,
        })
        setShowUploader(false)
      } catch {
        // Error handled by react-query / toast
      }
    },
    [patientId, createImage],
  )

  // ── Viewer navigation ──

  const openViewer = useCallback(
    (image: PatientImage) => {
      const idx = images.findIndex((img) => img.id === image.id)
      setSelectedIndex(idx)
      setViewerOpen(true)
    },
    [images],
  )

  const closeViewer = useCallback(() => {
    setViewerOpen(false)
    setSelectedIndex(-1)
  }, [])

  const goToPrev = useCallback(() => {
    if (selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1)
    }
  }, [selectedIndex])

  const goToNext = useCallback(() => {
    if (selectedIndex < images.length - 1) {
      setSelectedIndex(selectedIndex + 1)
    }
  }, [selectedIndex, images.length])

  // ── Delete handler ──

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteImage.mutateAsync({ patientId, id })
        // If deleting the last image, close viewer
        if (images.length <= 1) {
          closeViewer()
        } else if (selectedIndex >= images.length - 1) {
          // Deleting last item, shift back
          setSelectedIndex(images.length - 2)
        }
      } catch {
        // Error handled by react-query / toast
      }
    },
    [patientId, deleteImage, images.length, selectedIndex, closeViewer],
  )

  // ── State derivations ──

  const selectedImage = selectedIndex >= 0 && selectedIndex < images.length ? images[selectedIndex] : null
  const hasPrev = selectedIndex > 0
  const hasNext = selectedIndex < images.length - 1

  // ── Error state ──
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="mb-3 h-12 w-12 text-destructive opacity-40" />
        <p className="text-lg font-medium text-destructive">Error al cargar las imágenes</p>
        <p className="mt-2 text-sm">
          No se pudieron obtener las imágenes del paciente. Verifica la conexión e intenta de nuevo.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Imágenes</h3>
        <Button
          variant={showUploader ? 'outline' : 'default'}
          size="sm"
          onClick={() => setShowUploader(!showUploader)}
        >
          {showUploader ? (
            <>Cancelar</>
          ) : (
            <>
              <Camera className="mr-2 h-4 w-4" />
              Subir imagen
            </>
          )}
        </Button>
      </div>

      {/* Uploader — collapsible section */}
      {showUploader && (
        <div className="rounded-lg border bg-muted/20 p-4">
          <ImageUploader onUpload={handleUpload} isUploading={createImage.isPending} />
        </div>
      )}

      {/* Gallery */}
      <ImageGallery
        images={images}
        onImageClick={openViewer}
        loading={isLoading}
      />

      {/* Image viewer modal */}
      <ImageViewer
        open={viewerOpen}
        onClose={closeViewer}
        image={selectedImage}
        onPrev={hasPrev ? goToPrev : undefined}
        onNext={hasNext ? goToNext : undefined}
        hasPrev={hasPrev}
        hasNext={hasNext}
        onDelete={handleDelete}
      />
    </div>
  )
}
