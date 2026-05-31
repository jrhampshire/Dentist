import { useState, useRef, useCallback, type DragEvent, type ChangeEvent } from 'react'
import { Upload, X, FileImage } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import type { ImageType } from '@/types/dental-records'
import { IMAGE_TYPE_LABELS } from '@/types/dental-records'

const IMAGE_TYPES: ImageType[] = ['photo', 'xray_periapical', 'xray_panoramic', 'xray_cephalometric', 'document', 'other']
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf']
const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB

type UploadStatus = 'idle' | 'file_selected' | 'uploading' | 'done'

interface ImageUploaderProps {
  onUpload: (formData: FormData) => void
  isUploading?: boolean
}

export function ImageUploader({ onUpload, isUploading = false }: ImageUploaderProps) {
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<string | null>(null)
  const [imageType, setImageType] = useState<ImageType>('photo')
  const [toothFdi, setToothFdi] = useState<string>('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reset = () => {
    setStatus('idle')
    setSelectedFile(null)
    setFilePreview(null)
    setImageType('photo')
    setToothFdi('')
    setDescription('')
    setError(null)
    setDragOver(false)
    if (filePreview) URL.revokeObjectURL(filePreview)
  }

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(jpe?g|png|pdf)$/i)) {
      return 'Formato no permitido. Usa JPEG, PNG o PDF.'
    }
    if (file.size > MAX_FILE_SIZE) {
      return `El archivo excede el límite de 20 MB. Tamaño actual: ${(file.size / 1024 / 1024).toFixed(1)} MB.`
    }
    return null
  }

  const handleFileSelected = useCallback((file: File) => {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setSelectedFile(file)

    // Generate preview for images
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setFilePreview(url)
    } else {
      // PDF — no image preview
      setFilePreview(null)
    }

    setStatus('file_selected')
  }, [])

  // ── Drag & Drop handlers ──

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)

    const file = e.dataTransfer.files?.[0]
    if (file) handleFileSelected(file)
  }

  // ── Click to select ──

  const handleClickSelect = () => {
    fileInputRef.current?.click()
  }

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFileSelected(file)
  }

  // ── Submit ──

  const handleSubmit = () => {
    if (!selectedFile) return

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('image_type', imageType)
    if (toothFdi.trim()) {
      formData.append('tooth_fdi', toothFdi.trim())
    }
    if (description.trim()) {
      formData.append('description', description.trim())
    }

    setStatus('uploading')
    onUpload(formData)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  // "Done" state — show reset button
  if (status === 'done') {
    return (
      <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
        <div>
          <p className="font-medium text-green-800 dark:text-green-200">Imagen subida exitosamente</p>
          <p className="text-sm text-green-600 dark:text-green-400">{selectedFile?.name}</p>
        </div>
        <Button variant="outline" size="sm" onClick={reset}>
          Subir otra
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={status === 'idle' ? handleClickSelect : undefined}
        className={`
          relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8
          transition-colors duration-200
          ${dragOver
            ? 'border-primary bg-primary/5'
            : status === 'file_selected' || status === 'uploading'
              ? 'border-muted-foreground/30 bg-muted/20'
              : 'border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-muted/10'
          }
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.pdf"
          onChange={handleInputChange}
          className="hidden"
        />

        {status === 'uploading' ? (
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="font-medium">Subiendo imagen...</p>
            <p className="text-sm text-muted-foreground">{selectedFile?.name}</p>
          </div>
        ) : status === 'file_selected' ? (
          <div className="flex w-full flex-col items-center gap-3">
            {filePreview ? (
              <img
                src={filePreview}
                alt="Vista previa"
                className="max-h-48 max-w-full rounded-lg object-contain"
              />
            ) : (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <FileImage className="h-16 w-16" />
                <p className="text-sm">Vista previa no disponible</p>
              </div>
            )}
            <div className="text-center">
              <p className="font-medium">{selectedFile?.name}</p>
              <p className="text-sm text-muted-foreground">
                {selectedFile && formatFileSize(selectedFile.size)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                reset()
              }}
            >
              <X className="mr-1 h-3 w-3" />
              Cambiar archivo
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-center text-muted-foreground">
            <Upload className="h-10 w-10" />
            <div>
              <p className="font-medium">Arrastra una imagen aquí o haz clic para seleccionar</p>
              <p className="mt-1 text-sm">JPEG, PNG, PDF — Máx. 20 MB</p>
            </div>
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <X className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Metadata form — only when file is selected */}
      {status === 'file_selected' && (
        <div className="space-y-4 rounded-lg border bg-card p-4">
          <h4 className="font-medium">Metadatos de la imagen</h4>

          {/* Image type */}
          <div className="space-y-2">
            <Label htmlFor="image-type">Tipo de imagen</Label>
            <div className="flex flex-wrap gap-1.5">
              {IMAGE_TYPES.map((type) => (
                <Badge
                  key={type}
                  variant={imageType === type ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => setImageType(type)}
                >
                  {IMAGE_TYPE_LABELS[type]}
                </Badge>
              ))}
            </div>
          </div>

          {/* Tooth FDI */}
          <div className="space-y-2">
            <Label htmlFor="tooth-fdi">Diente FDI (opcional)</Label>
            <Input
              id="tooth-fdi"
              type="number"
              min={11}
              max={48}
              placeholder="Ej: 11, 46"
              value={toothFdi}
              onChange={(e) => setToothFdi(e.target.value)}
              className="max-w-[160px]"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Descripción (opcional)</Label>
            <textarea
              id="description"
              placeholder="Describe la imagen..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>

          {/* Submit */}
          <div className="flex gap-2">
            <Button onClick={handleSubmit} disabled={isUploading}>
              {isUploading ? 'Subiendo...' : 'Subir imagen'}
            </Button>
            <Button variant="ghost" onClick={reset}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
