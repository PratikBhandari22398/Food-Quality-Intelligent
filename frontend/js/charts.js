/**
 * Dashboard Visual Analytics - Chart.js Controller
 */

class DashboardCharts {
  constructor() {
    this.statusChart = null;
    this.timelineChart = null;
  }

  renderStatusPie(canvasId, pieData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    if (this.statusChart) {
      this.statusChart.destroy();
    }

    this.statusChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: pieData.labels,
        datasets: [{
          data: pieData.data,
          backgroundColor: pieData.colors,
          borderWidth: 2,
          borderColor: '#0B0F19'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#9CA3AF', font: { family: 'Inter', size: 12 } }
          }
        },
        cutout: '70%'
      }
    });
  }

  renderTimeline(canvasId, timelineData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    if (this.timelineChart) {
      this.timelineChart.destroy();
    }

    this.timelineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: timelineData.labels,
        datasets: [{
          label: 'Inspections Handled',
          data: timelineData.data,
          borderColor: '#6366F1',
          backgroundColor: 'rgba(99, 102, 241, 0.15)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#38BDF8'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9CA3AF' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9CA3AF' }, beginAtZero: true }
        }
      }
    });
  }
}

window.dashboardCharts = new DashboardCharts();
