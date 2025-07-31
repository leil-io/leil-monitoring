async function fetchCsv() {
	const csvData = await fetch(location.origin + "/chart.cgi?id=90200").then(res => res.text());

	const result = Papa.parse(csvData, { header: false });
	const rows = result.data.filter(row => row[0] && row[1]); // remove empty rows

	const labels = rows.map(row => new Date(row[0] * 1000).toLocaleTimeString());
	const memoryValues = rows.map(row => parseInt(row[1]) / (1024 * 1024)); // convert to MB

	// Create Chart
	new Chart(document.getElementById("memoryChart"), {
		type: 'line',
		data: {
			labels: labels,
			datasets: [{
				label: "Memory Usage (MB)",
				data: memoryValues,
				borderWidth: 2,
				fill: false,
				tension: 0.1
			}]
		},
		options: {
			responsive: true,
			scales: {
				y: {
					beginAtZero: true
				}
			}
		}
	});
}

fetchCsv()
