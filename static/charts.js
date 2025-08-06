const timeRange = Object.freeze({
	SHORT: {id: 0, name: "Short"}, // 1 minute interval
	MEDIUM: {id: 1, name: "Medium"}, // 6 minute interval
	LONG: {id: 2, name: "Long"}, // 30 minute interval
	VERYLONG: {id: 3, name: "Very Long"}, // 1 day interval
});

/**
 * @typedef UnitType
 * @type {object}
 * @property {number} NONE - Raw count
 * @property {number} BYTE - Byte/Bit count
 * @property {number} CPUTIME - CPU time (in microseconds)
 */

/** @type {UnitType} */
const dataUnit = Object.freeze({
	NONE: 0,
	BYTE: 1,
	CPUTIME: 3,
});


/**
 * @typedef ChartInfo
 * @type {object}
 * @property {string} name - Name of the chart
 * @property {number} id - ID of the chart for SFS backend
 * @property {string[]} labels - Label to use for chart
 * @property {UnitType} unit - Unit type of data
 */

/** @type {ChartInfo[]} */
let masterCharts = [
	{
		name: "cpu",
		id: 91000,
		labels: ["Userspace CPU %", "Kernelspace CPU %"],
		unit: dataUnit.CPUTIME,
	},
	{
		name: "memory",
		id: 90200,
		labels: ["Memory used"],
		unit: dataUnit.BYTE,
	},
	{
		name: "chunkDels",
		id: 90020,
		labels: ["Chunk deletions (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "chunkReps",
		id: 90030,
		labels: ["Chunk replications (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "statfs",
		id: 90040,
		labels: ["statfs operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "getattr",
		id: 90050,
		labels: ["getattr operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "setattr",
		id: 90060,
		labels: ["setattr operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "lookup",
		id: 90070,
		labels: ["lookup operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "mkdir",
		id: 90080,
		labels: ["mkdir operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "rmdir",
		id: 90090,
		labels: ["rmdir operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "symlink",
		id: 90100,
		labels: ["symlink operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "readlink",
		id: 90110,
		labels: ["readlink operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "mknod",
		id: 90120,
		labels: ["mknod operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "unlink",
		id: 90130,
		labels: ["unlink operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "rename",
		id: 90140,
		labels: ["rename operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "link",
		id: 90150,
		labels: ["link operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "readdir",
		id: 90160,
		labels: ["readdir operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "open",
		id: 90170,
		labels: ["open operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "read",
		id: 90180,
		labels: ["read operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "write",
		id: 90190,
		labels: ["write operations (per minute)"],
		unit: dataUnit.NONE,
	},
	{
		name: "packetsReceived",
		id: 90210,
		labels: ["Packets received (per second)"],
		unit: dataUnit.NONE,
	},
	{
		name: "packetsSent",
		id: 90220,
		labels: ["Packets sent (per second)"],
		unit: dataUnit.NONE,
	},
	{
		name: "bitsReceived",
		id: 90230,
		labels: ["Bits received (per second)"],
		unit: dataUnit.BYTE,
	},
	{
		name: "bitsSent",
		id: 90240,
		labels: ["Bits sent (per second)"],
		unit: dataUnit.BYTE,
	},
]

let chunkServerCharts = [
	{
		name: "cpu",
		id: 91000,
		labels: ["Userspace CPU %", "Kernelspace CPU %"],
		unit: dataUnit.CPUTIME,
	},
]

function bytePowerOf(num) {
	if (typeof num !== "number" || isNaN(num)) {
		return "N/A";
	}

	const units = ["", "K", "M", "G", "T", "P", "E", "Z"];
	let powerOf = 0
	for (let unit of units) {
		if (Math.abs(num) < 1024.0) {
			return [`${unit}B`, powerOf];
		}
		num /= 1024.0;
		powerOf++;
	}
	return `N/A`;
}

function setupLineChart(id, label, labels, data) {
	let datasets = []
	for (const [_, row] of data.entries()) {
		for (const [i, col] of row.entries()) {
			if (typeof label[i] === 'undefined') {
				continue
			}
			if (datasets.length < i + 1) {
				datasets.push({
					label: label[i],
					data: [],
					borderWidth: 2,
					fill: true,
					tension: 0.1
				})
			}
			datasets[i].data.push(col)
		}
	}

	let chart = Chart.getChart(id + "Chart")
	if (chart !== undefined) {
		chart.data.labels = labels
		chart.data.datasets = datasets
		chart.update()
		return
	} else {
		new Chart(document.getElementById(id + "Chart"), {
			type: 'line',
			data: {
				labels: labels,
				datasets: datasets
			},
			options: {
				responsive: true,
				scales: {
					x: {
						type: 'time',
						distribution: 'linear'
					},
					y: {
						beginAtZero: true
					},
				}

			}
		});
	}
}

function parseData(csvData) {
	const result = Papa.parse(csvData, { header: false, skipEmptyLines: true });
	const data = result.data.splice(1)

	return data.map(row =>
		row.map(cell => (cell === "" || cell === null || cell === undefined) ? 0 : cell)
	);
}

/**
 * @param {number} time - CPU time (microseconds)
 * @param {RangeValue} range
 * @returns {number} Percentage of usage
 */
function parseCPUtime(time, range) {
	let intervalSeconds = 0;
	switch (parseInt(range)) {
		case timeRange.SHORT.id:
			intervalSeconds = 60
			break;
		case timeRange.MEDIUM.id:
			intervalSeconds = 360
			break;
		case timeRange.LONG.id:
			intervalSeconds = 1800
			break;
		case timeRange.VERYLONG.id:
			intervalSeconds = 86400
			break;
		default:
			throw new Error("Invalid time range")
	}
	return ((time / (intervalSeconds * 1_000_000)) * 100).toFixed(2)
}

/**
 * @param {ChartInfo} chart
 * @param {object} timePeriod - What time range to use
 */
async function getData(chart, host, port, timePeriod) {
	const url = new URL("/chart.cgi", location.origin);
	url.searchParams.set("id", chart.id + parseInt(timePeriod));
	url.searchParams.set("host", host);
	url.searchParams.set("port", port);
	return fetch(url).then(res => res.text());
}

/**
 * @param {ChartInfo} chart - Chart to setup
 * @param {RangeValue} [range=timeRange.SHORT] - What time range to use
 */
async function setupChartInfo(chart, host, port, range = timeRange.SHORT.id) {
	const csvData = await getData(chart, host, port, range);
	const rows = parseData(csvData);
	const labels = rows.map(row => dateFns.fromUnixTime(row[0]))

	// TODO: A callback could be used here
	if (chart.unit == dataUnit.BYTE) {
		const [labelSize, power] = bytePowerOf(rows.reduce((max, row) => {
			let rowMaxSize = 0;
			for (const [i, cell] of row.entries()) {
				if (i === 0 || cell === 0) {
					continue // Skip timestamp and empty values
				}
				rowMaxSize = Math.max(rowMaxSize, cell)
			}
			return Math.max(max, rowMaxSize);
		}, 0))
		const values = rows.map(row => {
			let data = [];
			for (const [i, cell] of row.entries()) {
				if (i === 0) {
					continue // Skip timestamp
				}
				if (cell === 0) {
					data.push(cell)
				} else {
					data.push(parseInt(cell) / Math.pow(1024, power))
				}
			}
			return data
		});
		for (let [idx, _] of chart.labels.entries()) {
			chart.labels[idx] = `${chart.labels[idx]} (${labelSize})`
		}
		setupLineChart(chart.name, chart.labels, labels, values)
	} else if (chart.unit == dataUnit.NONE) {
		const values = rows.map(row => {
			let data = [];
			for (const [i, cell] of row.entries()) {
				if (i === 0) {
					continue // Skip timestamp
				}
				if (cell === 0) {
					data.push(cell)
				} else {
					data.push(cell, range)
				}
			}
			return data
		});
		for (let [idx, _] of chart.labels.entries()) {
			chart.labels[idx] = `${chart.labels[idx]}`
		}
		setupLineChart(chart.name, chart.labels, labels, values)

	} else if (chart.unit == dataUnit.CPUTIME) {
		const values = rows.map(row => {
			let data = [];
			for (const [i, cell] of row.entries()) {
				if (i === 0) {
					continue // Skip timestamp
				}
				if (cell === 0) {
					data.push(cell)
				} else {
					data.push(parseCPUtime(cell, range))
				}
			}
			return data
		});
		for (let [idx, _] of chart.labels.entries()) {
			chart.labels[idx] = `${chart.labels[idx]}`
		}
		setupLineChart(chart.name, chart.labels, labels, values)
	}
}

/**
 * @param {ChartInfo} chart - Chart to setup
 * @param {Element} chartContainer - Container for the chart
 * @returns HTMLDivElem - The new chart container
 */
function setupChart(chart, chartContainer) {
	const newChart = document.createElement('div');
	newChart.classList.add("chart-container");

	const canvas = document.createElement('canvas');
	canvas.id = chart.name + "Chart";
	newChart.appendChild(canvas);

	const chartOptions = document.createElement('div');
	chartOptions.classList.add("chart-options");
	chartOptions.dataset.chart = chart.name;
	chartOptions.dataset.chartlabel = chart.labels.join(",");
	chartOptions.dataset.chartunit = chart.unit;
	chartOptions.dataset.id = chart.id;
	for (const [_, value] of Object.entries(timeRange)) {
		const chartOption = document.createElement('div');
		chartOption.dataset.timeRange = value.id;
		chartOption.innerHTML = value.name;
		chartOption.classList.add("button");
		chartOptions.appendChild(chartOption);
	}
	newChart.appendChild(chartOptions);

	chartContainer.appendChild(newChart);
	return newChart;
}

// Dynamically load charts as needed
const observer = new IntersectionObserver(entries => {
	entries.forEach(entry => {
		if (entry.isIntersecting) {
			/** @type {ChartInfo} */
			const chart = JSON.parse(entry.target.dataset.chartinfo);
			const host = entry.target.closest(".chart-containers").dataset.host;
			const port = entry.target.closest(".chart-containers").dataset.port;
			setupChartInfo(chart, host, port);
			observer.unobserve(entry.target);
		}
	});
}, { threshold: 0.1 });



function setupCharts(elemQuery, charts) {
	document.querySelectorAll(elemQuery).forEach(elem => {
		charts.forEach(chart => {
			const host = elem.closest(".chart-containers").dataset.host;
			const port = elem.closest(".chart-containers").dataset.port;
			chart.name = chart.name + "_" + host + "_" + port + "_";
			const newChart = setupChart(chart, elem);
			newChart.dataset.chartinfo = JSON.stringify(chart);
			observer.observe(newChart);
		})
	});
}

setupCharts(".masterCharts > .chart-content", masterCharts);
setupCharts(".chunkServerCharts > .chart-content", chunkServerCharts);

document.querySelectorAll('.chart-options div').forEach(button => {
	button.addEventListener('click', function() {
		const chart = JSON.parse(button.parentElement.parentElement.dataset.chartinfo);
		const host = button.closest(".chart-containers").dataset.host;
		const port = button.closest(".chart-containers").dataset.port;
		const range =  this.dataset.timeRange;
		chart.name = chart.name + host + port;
		setupChartInfo(chart, host, port, range);
	});
});

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.chart-header').forEach(header => {
        header.addEventListener('click', function() {
            const content = this.nextElementSibling;
			if (content.classList.contains("show")) {
				content.classList.toggle('show');
				return;
			}
            content.classList.toggle('transition');
			setTimeout(() => {
				content.classList.toggle('transition');
				content.classList.toggle('show');
			}, 500); {
			}
        });
    });
});
