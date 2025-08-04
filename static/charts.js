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
 */

/** @type {UnitType} */
const dataUnit = Object.freeze({
	NONE: 0,
	BYTE: 1,
	BIT: 2,
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
		name: "memory",
		id: 90200,
		labels: ["Memory used"],
		unit: dataUnit.BYTE,
	},
	// {
	// 	name: "cpu",
	// 	id: 91001,
	// 	labels: ["Userspace CPU %", "Kernelspace CPU %"],
	// 	unit: dataUnit.BYTE,
	// }
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

function setupSingleLineChart(id, label, labels, data) {
	let chart = Chart.getChart(id + "Chart")
	if (chart !== undefined) {
		chart.data.labels = labels
		chart.data.datasets[0].label = label
		chart.data.datasets[0].data = data
		chart.update()
		return
	} else {
		new Chart(document.getElementById(id + "Chart"), {
			type: 'line',
			data: {
				labels: labels,
				datasets: [
					{
						label: label,
						data: data,
						borderWidth: 2,
						fill: true,
						tension: 0.1
					}
				]
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
	const result = Papa.parse(csvData, { header: false });
	return result.data.filter(row => row[0] && row[1]); // remove empty rows
}

/**
 * @param {ChartInfo} chart
 * @param {object} timePeriod - What time range to use
 */
async function getMasterData(chart, timePeriod) {
	const url = new URL("/chart.cgi", location.origin);
	url.searchParams.set("id", chart.id + parseInt(timePeriod));
	const existingParams = new URLSearchParams(location.search);
	if (existingParams.has("masterhost")) {
		url.searchParams.set("host", existingParams.get("masterhost"));
	}
	if (existingParams.has("masterport")) {
		url.searchParams.set("port", existingParams.get("masterport"));
	}
	return fetch(url).then(res => res.text());
}

/**
 * @param {ChartInfo} chart - Chart to setup
 * @param {RangeValue} [range=timeRange.SHORT] - What time range to use
 */
async function setupChartInfo(chart, range = timeRange.SHORT.id) {
	const csvData = await getMasterData(chart, range)
	let values;
	const rows = parseData(csvData)
	const labels = rows.map(row => dateFns.fromUnixTime(row[0]))
	if (chart.unit == dataUnit.BYTE) {
		const [labelSize, power] = bytePowerOf(rows.reduce((max, row) => {
			return Math.max(max, row[1]);
		}, 0))
		values = rows.map(row => parseInt(row[1]) / Math.pow(1024, power));
		setupSingleLineChart(chart.name, `${chart.labels[0]} (${labelSize})`, labels, values)
	}
}

/**
 * @param {ChartInfo} chart - Chart to setup
 * @param {string} chartContainerId - Container for the chart
 */
function setupChart(chart, chartContainerId) {
	const chartContainer = document.getElementById(chartContainerId)
	const newChart = document.createElement('div')
	newChart.classList.add("chart-container")

	const canvas = document.createElement('canvas')
	canvas.id = chart.name + "Chart"
	newChart.appendChild(canvas)

	const chartOptions = document.createElement('div')
	chartOptions.classList.add("chart-options")
	chartOptions.dataset.chart = chart.name
	chartOptions.dataset.chartlabel = chart.labels.join(",")
	chartOptions.dataset.chartunit = chart.unit
	chartOptions.dataset.id = chart.id
	for (const [_, value] of Object.entries(timeRange)) {
		const chartOption = document.createElement('div')
		chartOption.dataset.timeRange = value.id
		chartOption.innerHTML = value.name
		chartOptions.appendChild(chartOption)
	}
	newChart.appendChild(chartOptions)

	chartContainer.appendChild(newChart)
	setupChartInfo(chart)
}

for (const chart of masterCharts) {
	setupChart(chart, "masterCharts")
}

document.querySelectorAll('.chart-options div').forEach(button => {
	button.addEventListener('click', function() {
		/** @type ChartInfo */
		const chart = {
			name: button.parentElement.dataset.chart,
			labels: button.parentElement.dataset.chartlabel.split(","),
			id: parseInt(button.parentElement.dataset.id),
			unit: button.parentElement.dataset.chartunit,
		}
		const range =  this.dataset.timeRange
		setupChartInfo(chart, range)
	});
});
