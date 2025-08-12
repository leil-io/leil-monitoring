/**
 * @typedef SFSRange
 * @type {object}
 * @property {number} id - SaunaFS id for range
 * @property {number} name - Human readable name
 */

/**
 * @typedef SFSRanges
 * @type {object}
 * @property {Range} SHORT - 1 minute interval
 * @property {Range} MEDIUM - 6 minute interval
 * @property {Range} LONG - 30 minute interval
 * @property {Range} VERYLONG - 1 day interval
 */


/** @type {SFSRanges} */
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
 * @property {number} BYTE - Byte count
 * @property {number} BIT - Bit count
 * @property {number} CPUTIME - CPU time (in microseconds)
 */

/** @type {UnitType} */
const dataUnit = Object.freeze({
	NONE: 0,
	BYTE: 1,
	CPUTIME: 3,
	TIME: 4,
});


/**
 * @typedef ChartInfo
 * @type {object}
 * @property {string} name - Name of the chart
 * @property {number} id - ID of the chart for SFS backend
 * @property {string[]} labels - Label to use for chart
 * @property {UnitType} unit - Unit type of data
 * @property {boolean} rate - Whether the value is rate
 */

/** @type {ChartInfo[]} */
let masterCharts = [
	{
		name: "cpu",
		id: 91000,
		labels: ["Userspace CPU %", "Kernelspace CPU %"],
		unit: dataUnit.CPUTIME,
		rate: false,
	},
	{
		name: "memory",
		id: 90200,
		labels: ["Memory used"],
		unit: dataUnit.BYTE,
		rate: false,
	},
	{
		name: "chunkDels",
		id: 90020,
		labels: ["Chunk deletions"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "chunkReps",
		id: 90030,
		labels: ["Chunk replications"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "statfs",
		id: 90040,
		labels: ["statfs operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "getattr",
		id: 90050,
		labels: ["getattr operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "setattr",
		id: 90060,
		labels: ["setattr operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "lookup",
		id: 90070,
		labels: ["lookup operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "mkdir",
		id: 90080,
		labels: ["mkdir operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "rmdir",
		id: 90090,
		labels: ["rmdir operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "symlink",
		id: 90100,
		labels: ["symlink operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "readlink",
		id: 90110,
		labels: ["readlink operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "mknod",
		id: 90120,
		labels: ["mknod operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "unlink",
		id: 90130,
		labels: ["unlink operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "rename",
		id: 90140,
		labels: ["rename operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "link",
		id: 90150,
		labels: ["link operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "readdir",
		id: 90160,
		labels: ["readdir operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "open",
		id: 90170,
		labels: ["open operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "read",
		id: 90180,
		labels: ["read operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "write",
		id: 90190,
		labels: ["write operations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "packetsReceived",
		id: 90210,
		labels: ["Packets received (per second)"],
		unit: dataUnit.NONE,
		rate: true,
	},
	{
		name: "packetsSent",
		id: 90220,
		labels: ["Packets sent (per second)"],
		unit: dataUnit.NONE,
		rate: true,
	},
	{
		name: "bytesReceived",
		id: 90230,
		labels: ["Bits received (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "bytesSent",
		id: 90240,
		labels: ["Bits sent (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
]

let chunkServerCharts = [
	{
		name: "cpu",
		id: 91000,
		labels: ["Userspace CPU %", "Kernelspace CPU %"],
		unit: dataUnit.CPUTIME,
		rate: false,
	},
	{
		name: "bytesReceivedClient",
		id: 91010,
		labels: ["Client/Chunkserver bytes received (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "bytesSentClient",
		id: 91020,
		labels: ["Client/Chunkserver bytes sent (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "bytesReadOverhead",
		id: 91030,
		labels: ["Bytes read total (per second)", "Bytes read overhead (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "bytesWrittenOverhead",
		id: 91040,
		labels: ["Bytes written total (per second)", "Bytes written overhead (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "bytesReceivedMaster",
		id: 90020,
		labels: ["Bytes received from master (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "bytesSentMaster",
		id: 90030,
		labels: ["Bytes sent to master (per second)"],
		unit: dataUnit.BYTE,
		rate: true,
	},
	{
		name: "lowLevelReadOps",
		id: 91050,
		labels: ["Low-level read operations total", "Low-level read operations overhead"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "lowLevelWriteOps",
		id: 91060,
		labels: ["Low-level write operations total", "Low-level write operations overhead"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "highLevelWriteOps",
		id: 90170,
		labels: ["High-level write operations total"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "dataReadTime",
		id: 90180,
		labels: ["Time of data read operations"],
		unit: dataUnit.TIME,
		rate: true,
	},
	{
		name: "dataWriteTime",
		id: 90190,
		labels: ["Time of data write operations"],
		unit: dataUnit.TIME,
		rate: true,
	},
	{
		name: "chunkReplications",
		id: 90200,
		labels: ["Number of chunk replications"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "chunkCreations",
		id: 90210,
		labels: ["Number of chunk creations"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "chunkDeletions",
		id: 90220,
		labels: ["Number of chunk deletions"],
		unit: dataUnit.NONE,
		rate: false,
	},
	{
		name: "chunkTests",
		id: 90270,
		labels: ["Number of chunk tests"],
		unit: dataUnit.NONE,
		rate: false,
	},
	// {
	// 	name: "memory",
	// 	id: 90300,
	// 	labels: ["Memory used"],
	// 	unit: dataUnit.BYTE,
	// },
]

function secondPowerOf(num) {
	if (typeof num !== "number" || isNaN(num)) {
		return "N/A";
	}
	const suffix = "s"

	const units = ["μ", "m"];
	let powerOf = 0
	for (let unit of units) {
		if (unit == units[units.length - 1]) {
			return [`${unit}${suffix}`, powerOf];
		}
		if (Math.abs(num) < 1000) {
			return [`${unit}${suffix}`, powerOf];
		}
		num /= 1000;
		powerOf++;
	}
	return `N/A`;
}

function bytePowerOf(num, unitType) {
	if (typeof num !== "number" || isNaN(num)) {
		return "N/A";
	}

	const units = ["", "K", "M", "G", "T", "P", "E", "Z"];
	let powerOf = 0
	for (let unit of units) {
		if (Math.abs(num) < 1024.0) {
			let suffix = "N/A"
			if (unitType === dataUnit.BIT) {
				suffix = "b"
			} else if (unitType == dataUnit.BYTE) {
				suffix = "B"
			}
			return [`${unit}${suffix}`, powerOf];
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

	let chart = Chart.getChart(id)
	if (chart !== undefined) {
		chart.data.labels = labels
		chart.data.datasets = datasets
		chart.update()
		return
	} else {
		new Chart(document.getElementById(id), {
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

function getIntervalFromData(rows) {
	// We trust the timestamps are consistent
	if (rows.length < 2) throw new Error("Not enough rows to determine interval");
	return rows[1][0] - rows[0][0];
}

function parseData(csvData) {
	const result = Papa.parse(csvData, { header: false, skipEmptyLines: true });
	const data = result.data.splice(1)

	return data.map(row =>
		row.map(cell => (cell === "" || cell === null || cell === undefined) ? 0 : cell)
	);
}

/**
 * @param {number} Range enum id
 * @returns {number} Seconds in interval
 */
function getIntervalSecs(range) {
	switch (parseInt(range)) {
		case timeRange.SHORT.id:
			return 60
		case timeRange.MEDIUM.id:
			return 360
		case timeRange.LONG.id:
			return 1800
		case timeRange.VERYLONG.id:
			return 86400
		default:
			throw new Error("Invalid time range")
	}
}

/**
 * @param {number} time - CPU time (microseconds)
 * @param {number} range - Range enum id
 * @returns {number} Percentage of usage
 */
function parseCPUtime(time, range) {
	let intervalSeconds = getIntervalSecs(range);
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
 * @param {number} [range=timeRange.SHORT.id] - What time range to use
 */
/**
 * @param {ChartInfo} chart - Chart to setup
 * @param {number} [range=timeRange.SHORT.id] - What time range to use
 */
async function setupChartInfo(chart, host, port, range = timeRange.SHORT.id) {
	const csvData = await getData(chart, host, port, range);
	const rows = parseData(csvData);
	const intervalSecs = getIntervalFromData(rows)

	// X-axis labels (timestamps -> Date)
	const labels = rows.map(row => dateFns.fromUnixTime(row[0]));

	// Helper: iterate cells (skip timestamp), allowing per-cell transform to return
	// either a scalar or an array of scalars (we flatten).
	const mapCellValues = (rows, transform, rate=false) =>
		rows.map(row => {
			const out = [];
			for (let i = 1; i < row.length; i += 1) {
				const cell = row[i];
				let v = cell === 0 ? 0 : transform(cell, range);
				if (v !== 0 && rate) {
					v = v / intervalSecs
				}
				if (Array.isArray(v)) out.push(...v);
					else out.push(v);
			}
			return out;
		});

	// Helper: label formatting without mutating the original array
	const withSuffix = (labels, suffix = "") =>
		labels.map(l => (suffix ? `${l} ${suffix}` : `${l}`));

	// Helper: Find peak magnitude across all non-zero cells
	const peakMagnitude = (rows) => {
		return rows.reduce((max, row) => {
				let rowMax = 0;
				for (let i = 1; i < row.length; i += 1) {
					rowMax = Math.max(rowMax, row[i] || 0);
				}
				return Math.max(max, rowMax);
			}, 0);
	}

	// Branch by unit
	switch (chart.unit) {
		case dataUnit.BYTE:
		case dataUnit.BIT: {
			let maxVal = peakMagnitude(rows)
			if (maxVal !== 0 && chart.rate) {
				maxVal = maxVal / intervalSecs
			}

			const [labelSize, power] = bytePowerOf(maxVal, chart.unit);

			const values = mapCellValues(rows, cell =>
				parseInt(cell, 10) / Math.pow(1024, power)
			, chart.rate);

			const yLabels = withSuffix(chart.labels, `(${labelSize})`);
			setupLineChart(chart.name, yLabels, labels, values);
			return;
		}

		case dataUnit.NONE: {
			const values = mapCellValues(rows, (cell, rng) => [cell], chart.rate);
			const yLabels = withSuffix(chart.labels);
			setupLineChart(chart.name, yLabels, labels, values);
			return;
		}

		case dataUnit.CPUTIME: {
			const values = mapCellValues(rows, (cell, rng) => parseCPUtime(cell, rng), chart.rate);
			const yLabels = withSuffix(chart.labels);
			setupLineChart(chart.name, yLabels, labels, values);
			return;
		}

		case dataUnit.TIME: {
			let maxVal = peakMagnitude(rows)

			if (maxVal !== 0 && chart.rate) {
				maxVal = maxVal / intervalSecs
			}

			const [labelSize, power] = secondPowerOf(maxVal);

			const values = mapCellValues(rows, cell =>
				parseInt(cell, 10) / Math.pow(1000, power)
			, chart.rate);

			const yLabels = withSuffix(chart.labels, `(${labelSize})`);
			setupLineChart(chart.name, yLabels, labels, values);
			return;
		}

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
	canvas.id = chart.name;
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
			chart.name = chart.name + "_" + host + "_" + port + "_" + "Chart";
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
		const range =  this.dataset.timeRange
		chart.name = chart.name
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
