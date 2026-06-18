import { useState } from "react";
import { Plus, Lock, FileText } from "lucide-react";
import {
	useClinicalNotes,
	useCreateClinicalNote,
	useSignClinicalNote,
} from "@/hooks/useClinicalNotes";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NOTE_TYPE_LABELS, type NoteType } from "@/types";
import { formatDateTime } from "@/lib/utils";

interface ClinicalNotesTabProps {
	patientId: string;
}

export function ClinicalNotesTab({ patientId }: ClinicalNotesTabProps) {
	const [dialogOpen, setDialogOpen] = useState(false);
	const [newNoteType, setNewNoteType] = useState<NoteType>("evolution");
	const [newTitle, setNewTitle] = useState("");
	const [newContent, setNewContent] = useState("");
	const [signingNoteId, setSigningNoteId] = useState<string | null>(null);

	const { data: notes, isLoading } = useClinicalNotes(patientId);
	const createNote = useCreateClinicalNote();
	const signNote = useSignClinicalNote();

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!newTitle.trim() || !newContent.trim()) return;

		await createNote.mutateAsync({
			patientId,
			data: { note_type: newNoteType, title: newTitle, content: newContent },
		});
		setDialogOpen(false);
		setNewTitle("");
		setNewContent("");
		setNewNoteType("evolution");
	};

	const handleSign = async (noteId: string) => {
		setSigningNoteId(noteId);
		try {
			await signNote.mutateAsync({ patientId, noteId });
		} finally {
			setSigningNoteId(null);
		}
	};

	const getTypeBadge = (type: NoteType) => {
		const variants: Record<
			NoteType,
			"info" | "success" | "warning" | "secondary" | "default"
		> = {
			evolution: "info",
			diagnosis: "warning",
			treatment: "success",
			observation: "secondary",
			consent: "default",
		};
		return <Badge variant={variants[type]}>{NOTE_TYPE_LABELS[type]}</Badge>;
	};

	if (isLoading) {
		return (
			<div className="flex justify-center py-8">
				<div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
			</div>
		);
	}

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<h3 className="text-lg font-semibold">Notas Clínicas</h3>
				<Button onClick={() => setDialogOpen(true)}>
					<Plus className="mr-2 h-4 w-4" />
					Nueva Nota
				</Button>
			</div>

			<Card>
				<CardContent className="p-0">
					{!notes || notes.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
							<FileText className="h-12 w-12 mb-3 opacity-40" />
							<p>No hay notas clínicas registradas</p>
						</div>
					) : (
						<Table>
							<TableHeader>
								<TableRow>
									<TableHead>Tipo</TableHead>
									<TableHead>Título</TableHead>
									<TableHead>Contenido</TableHead>
									<TableHead>Autor</TableHead>
									<TableHead>Fecha</TableHead>
									<TableHead>Estado</TableHead>
									<TableHead className="text-right">Acciones</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{notes.map((note) => (
									<TableRow key={note.id}>
										<TableCell>{getTypeBadge(note.note_type)}</TableCell>
										<TableCell className="font-medium">{note.title}</TableCell>
										<TableCell className="max-w-xs truncate text-muted-foreground">
											{note.content?.substring(0, 80)}
											{note.content?.length > 80 ? "..." : ""}
										</TableCell>
										<TableCell>{note.author_name || "—"}</TableCell>
										<TableCell className="text-sm text-muted-foreground">
											{formatDateTime(note.created_at)}
										</TableCell>
										<TableCell>
											{note.is_signed ? (
												<Badge variant="signed">
													<Lock className="mr-1 h-3 w-3" />
													Firmada
												</Badge>
											) : (
												<Badge variant="pending">Pendiente</Badge>
											)}
										</TableCell>
										<TableCell className="text-right">
											{!note.is_signed ? (
												<Button
													variant="outline"
													size="sm"
													disabled={signingNoteId === note.id}
													onClick={() => handleSign(note.id)}
												>
													{signingNoteId === note.id ? (
														<div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
													) : (
														"Firmar"
													)}
												</Button>
											) : (
												<Lock className="h-4 w-4 text-muted-foreground" />
											)}
										</TableCell>
									</TableRow>
								))}
							</TableBody>
						</Table>
					)}
				</CardContent>
			</Card>

			{/* Create Note Dialog */}
			<Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Nueva Nota Clínica</DialogTitle>
					</DialogHeader>
					<form onSubmit={handleCreate} className="space-y-4">
						<div className="space-y-2">
							<Label htmlFor="note_type">Tipo de nota</Label>
							<select
								id="note_type"
								value={newNoteType}
								onChange={(e) => setNewNoteType(e.target.value as NoteType)}
								className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
							>
								{Object.entries(NOTE_TYPE_LABELS).map(([value, label]) => (
									<option key={value} value={value}>
										{label}
									</option>
								))}
							</select>
						</div>
						<div className="space-y-2">
							<Label htmlFor="title">Título</Label>
							<Input
								id="title"
								value={newTitle}
								onChange={(e) => setNewTitle(e.target.value)}
								required
							/>
						</div>
						<div className="space-y-2">
							<Label htmlFor="content">Contenido</Label>
							<textarea
								id="content"
								value={newContent}
								onChange={(e) => setNewContent(e.target.value)}
								rows={5}
								className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
								required
							/>
						</div>
						<Button
							type="submit"
							className="w-full"
							disabled={createNote.isPending}
						>
							{createNote.isPending ? "Creando..." : "Crear nota"}
						</Button>
					</form>
				</DialogContent>
			</Dialog>
		</div>
	);
}
