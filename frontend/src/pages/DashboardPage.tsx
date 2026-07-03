import { Link } from "react-router-dom";
import {
	CalendarDays,
	Users,
	FileText,
	AlertTriangle,
	TrendingUp,
	Clock,
	DollarSign,
	RefreshCw,
} from "lucide-react";
import {
	LineChart,
	Line,
	BarChart,
	Bar,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	ResponsiveContainer,
} from "recharts";
import { useAuth } from "@/hooks/useAuth";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function StatCardSkeleton() {
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
				<div className="h-4 w-24 animate-pulse rounded bg-muted" />
				<div className="h-8 w-8 animate-pulse rounded bg-muted" />
			</CardHeader>
			<CardContent>
				<div className="h-8 w-16 animate-pulse rounded bg-muted" />
			</CardContent>
		</Card>
	);
}

// ---------------------------------------------------------------------------
// Stat Card
// ---------------------------------------------------------------------------

interface StatCardProps {
	title: string;
	value: string;
	icon: React.ComponentType<{ className?: string }>;
	color: string;
	bgColor: string;
}

function StatCard({ title, value, icon: Icon, color, bgColor }: StatCardProps) {
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
				<CardTitle className="text-sm font-medium">{title}</CardTitle>
				<div className={`${bgColor} rounded-md p-2`}>
					<Icon className={`h-4 w-4 ${color}`} />
				</div>
			</CardHeader>
			<CardContent>
				<div className="text-2xl font-bold">{value}</div>
			</CardContent>
		</Card>
	);
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_LABELS: Record<string, string> = {
	scheduled: "Programada",
	confirmed: "Confirmada",
	in_progress: "En curso",
	completed: "Completada",
	cancelled: "Cancelada",
	no_show: "No asistió",
};

const STATUS_COLORS: Record<string, string> = {
	scheduled: "bg-blue-100 text-blue-800",
	confirmed: "bg-green-100 text-green-800",
	in_progress: "bg-yellow-100 text-yellow-800",
	completed: "bg-gray-100 text-gray-800",
};

function StatusBadge({ status }: { status: string }) {
	return (
		<span
			className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${STATUS_COLORS[status] || "bg-gray-100 text-gray-800"}`}
		>
			{STATUS_LABELS[status] || status}
		</span>
	);
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function DashboardPage() {
	const { user, isAdmin, isRecepcionista } = useAuth();
	const { data: metrics, isLoading, isError, refetch } = useDashboardMetrics();

	// ── Loading state ──────────────────────────────────────────────────────
	if (isLoading) {
		return (
			<div className="space-y-6">
				<div>
					<h2 className="text-2xl font-bold tracking-tight">
						Cargando dashboard…
					</h2>
				</div>
				<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
					{Array.from({ length: 4 }).map((_, i) => (
						<StatCardSkeleton key={i} />
					))}
				</div>
			</div>
		);
	}

	// ── Error state ────────────────────────────────────────────────────────
	if (isError || !metrics) {
		return (
			<div className="flex flex-col items-center justify-center py-16 gap-4">
				<p className="text-muted-foreground">
					No se pudieron cargar las métricas.
				</p>
				<Button variant="outline" onClick={() => refetch()}>
					<RefreshCw className="mr-2 h-4 w-4" />
					Reintentar
				</Button>
			</div>
		);
	}

	// ── Stats ──────────────────────────────────────────────────────────────
	const stats: StatCardProps[] = [
		{
			title: "Citas hoy",
			value: metrics.appointments_today.toString(),
			icon: CalendarDays,
			color: "text-blue-600",
			bgColor: "bg-blue-50",
		},
		{
			title: "Pacientes totales",
			value: metrics.patients_total.toString(),
			icon: Users,
			color: "text-green-600",
			bgColor: "bg-green-50",
		},
		{
			title: "Alertas inventario",
			value: (metrics.low_stock_count + metrics.expiring_soon_count).toString(),
			icon: AlertTriangle,
			color: "text-amber-600",
			bgColor: "bg-amber-50",
		},
		{
			title: "Ingresos del mes",
			value: formatCurrency(Number(metrics.revenue_this_month)),
			icon: DollarSign,
			color: "text-purple-600",
			bgColor: "bg-purple-50",
		},
	];

	// ── Chart: does data exist? ────────────────────────────────────────────
	const hasRevenue = metrics.revenue_trend.some((p) => p.total > 0);
	const hasAppointments = metrics.appointments_trend.some((p) => p.count > 0);

	return (
		<div className="space-y-6">
			{/* Welcome */}
			<div>
				<h2 className="text-2xl font-bold tracking-tight">
					Bienvenido, {user?.first_name || "Usuario"}
				</h2>
				<p className="text-muted-foreground">
					Resumen de tu clínica —{" "}
					{new Date().toLocaleDateString("es-MX", {
						weekday: "long",
						year: "numeric",
						month: "long",
						day: "numeric",
					})}
				</p>
			</div>

			{/* Stats Grid */}
			<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
				{stats.map((stat) => (
					<StatCard key={stat.title} {...stat} />
				))}
			</div>

			{/* Charts */}
			<div className="grid gap-4 md:grid-cols-2">
				{/* Revenue Trend */}
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<TrendingUp className="h-5 w-5 text-green-600" />
							Ingresos (últimos 30 días)
						</CardTitle>
					</CardHeader>
					<CardContent>
						{hasRevenue ? (
							<ResponsiveContainer width="100%" height={220}>
								<LineChart data={metrics.revenue_trend}>
									<CartesianGrid
										strokeDasharray="3 3"
										className="stroke-muted"
									/>
									<XAxis
										dataKey="date"
										tickFormatter={(d: string) => {
											const [, month, day] = d.split("-");
											return `${day}/${month}`;
										}}
										className="text-xs"
									/>
									<YAxis className="text-xs" />
									<Tooltip
									formatter={(_value: unknown) =>
										formatCurrency(_value as number)
									}
										labelFormatter={(_label: unknown) =>
											formatDate(String(_label), "dd/MM/yyyy")
										}
									/>
									<Line
										type="monotone"
										dataKey="total"
										stroke="#10B981"
										strokeWidth={2}
										dot={false}
									/>
								</LineChart>
							</ResponsiveContainer>
						) : (
							<p className="text-sm text-muted-foreground py-8 text-center">
								No hay datos de ingresos en el período.
							</p>
						)}
					</CardContent>
				</Card>

				{/* Appointments Trend */}
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<CalendarDays className="h-5 w-5 text-blue-600" />
							Citas por día (últimos 30 días)
						</CardTitle>
					</CardHeader>
					<CardContent>
						{hasAppointments ? (
							<ResponsiveContainer width="100%" height={220}>
								<BarChart data={metrics.appointments_trend}>
									<CartesianGrid
										strokeDasharray="3 3"
										className="stroke-muted"
									/>
									<XAxis
										dataKey="date"
										tickFormatter={(d: string) => {
											const [, month, day] = d.split("-");
											return `${day}/${month}`;
										}}
										className="text-xs"
									/>
									<YAxis allowDecimals={false} className="text-xs" />
									<Tooltip
										labelFormatter={(_label: unknown) =>
											formatDate(String(_label), "dd/MM/yyyy")
										}
									/>
									<Bar dataKey="count" fill="#4A90D9" radius={[4, 4, 0, 0]} />
								</BarChart>
							</ResponsiveContainer>
						) : (
							<p className="text-sm text-muted-foreground py-8 text-center">
								No hay datos de citas en el período.
							</p>
						)}
					</CardContent>
				</Card>
			</div>

			{/* Upcoming Appointments */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Clock className="h-5 w-5" />
						Próximas citas (7 días)
					</CardTitle>
				</CardHeader>
				<CardContent>
					{metrics.upcoming_appointments.length === 0 ? (
						<p className="text-sm text-muted-foreground">
							No hay citas programadas para los próximos 7 días.
						</p>
					) : (
						<div className="space-y-3">
							{metrics.upcoming_appointments.map((a) => (
								<div
									key={a.id}
									className="flex items-center justify-between rounded-lg border p-3"
								>
									<div>
										<p className="font-medium">{a.patient_name}</p>
										<p className="text-sm text-muted-foreground">
											{a.type_name}
										</p>
									</div>
									<div className="text-right">
										<p className="font-medium">{a.time}</p>
										<p className="text-xs text-muted-foreground">
											{formatDate(a.date, "dd/MM")}
										</p>
										<StatusBadge status={a.status} />
									</div>
								</div>
							))}
						</div>
					)}
				</CardContent>
			</Card>

			{/* Quick Actions */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<TrendingUp className="h-5 w-5" />
						Acciones rápidas
					</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
						<Link to="/patients">
							<Button variant="outline" className="w-full justify-start">
								<Users className="mr-2 h-4 w-4" />
								Nuevo paciente
							</Button>
						</Link>
						<Link to="/appointments">
							<Button variant="outline" className="w-full justify-start">
								<CalendarDays className="mr-2 h-4 w-4" />
								Agendar cita
							</Button>
						</Link>
						{(isAdmin || isRecepcionista) && (
							<Link to="/invoices">
								<Button variant="outline" className="w-full justify-start">
									<FileText className="mr-2 h-4 w-4" />
									Nueva factura
								</Button>
							</Link>
						)}
						{isAdmin && (
							<Link to="/inventory">
								<Button variant="outline" className="w-full justify-start">
									<AlertTriangle className="mr-2 h-4 w-4" />
									Ver alertas
								</Button>
							</Link>
						)}
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
