const timeRange = Object.freeze({
    SHORT: 0,
    MEDIUM: 1,
    LONG: 2,
    VERYLONG: 3,
});

const dataUnit = Object.freeze({
    NONE: 0,
    BYTE: 1,
    BIT: 2,
});


let masterChartIds = {
	memory: {
		id: 90200,
		label: "Memory used",
		unit: dataUnit.BYTE,
	},
}

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

async function getMasterData(chartName, timePeriod) {
	const url = new URL("/chart.cgi", location.origin);
	url.searchParams.set("id", masterChartIds[chartName].id + parseInt(timePeriod));
	const existingParams = new URLSearchParams(location.search);
	if (existingParams.has("masterhost")) {
		url.searchParams.set("host", existingParams.get("masterhost"));
	}
	if (existingParams.has("masterport")) {
		url.searchParams.set("port", existingParams.get("masterport"));
	}
	return fetch(url).then(res => res.text());
}

async function setupChart(type, labelPrefix, dataType, range = timeRange.SHORT) {
	const csvData = await getMasterData("memory", range)
	console.log(csvData)
	let values;
	const rows = parseData(csvData)
	const labels = rows.map(row => dateFns.fromUnixTime(row[0]))
	if (dataType == dataUnit.BYTE) {
		const [labelSize, power] = bytePowerOf(rows.reduce((max, row) => Math.max(max, row[1]), 0))
		values = rows.map(row => parseInt(row[1]) / Math.pow(1024, power));
		setupSingleLineChart(type, `${labelPrefix} (${labelSize})`, labels, values)
	}
}

setupChart("memory", "Memory used", dataUnit.BYTE)

document.querySelectorAll('.chart-options div').forEach(button => {
	button.addEventListener('click', function() {
		const range =  this.dataset.timeRange
		const chartName =  button.parentElement.dataset.chart;
		const chartLabel = button.parentElement.dataset.chartlabel;
		const chartUnit =  button.parentElement.dataset.chartunit;
		setupChart(chartName, chartLabel, chartUnit, range)
	});
});
