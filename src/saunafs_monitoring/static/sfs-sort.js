function ToggleMountInfo(rowId) {
	const row = document.getElementById(rowId);
	if (row) {
		if (row.style.display === 'none') {
			row.style.display = 'table-row';
		} else {
			row.style.display = 'none';
		}
	}
}

function getCellValue(tr, idx) {
	const cell = tr.children[idx];
	if (!cell) return '';

	const raw = (cell.innerText || cell.textContent || '').trim();

	// normalize weird spaces and thousands separators
	const text = raw.replace(/\u00A0/g, ' ').replace(/,/g, '').trim();

	// bytes (binary or decimal) with optional "/s"
	// examples it will handle: "652.3 MB/s", "17.7 MiB/s", "512 KiB", "123 B"
	const bytesRe = /^([\d.]+)\s*([KMGTPE]?)(i?)B(?:\/s)?$/i;

	const ipRe = /^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$/i

	// plain number with optional "/s" (e.g. "0.0/s")
	const rateRe = /^([\d.]+)\s*(?:\/s)?$/i;

	let m = text.match(bytesRe);
	if (m) {
		const value = parseFloat(m[1]);
		const unitLetter = m[2].toUpperCase(); // '', K, M, G, T, P, E
		const isBinary = !!m[3];               // 'i' present => KiB, MiB, ...
			const order = ['', 'K', 'M', 'G', 'T', 'P', 'E'].indexOf(unitLetter);
		const base = isBinary ? 1024 : 1000;
		const factor = order > 0 ? Math.pow(base, order) : 1;
		return value * factor; // always a number of bytes (or bytes/sec if original had "/s")
	}

	if (text.match(ipRe)) {
		// TODO(Urmas): Sort by IP address ranges
		return text;
	}

	m = text.match(rateRe);
	if (m) {
		return parseFloat(m[1]); // treat bare numbers like numbers
	}

	// last resort: string
	return text;
}

function comparer(idx, asc) {
	return function(a, b) {
		const v1 = getCellValue(asc ? a : b, idx);
		const v2 = getCellValue(asc ? b : a, idx);
		const n1 = typeof v1 === 'number' && !isNaN(v1);
		const n2 = typeof v2 === 'number' && !isNaN(v2);
		if (n1 && n2) return v1 - v2;
		return String(v1).localeCompare(String(v2), undefined, { numeric: true, sensitivity: 'base' });
	};
}

document.querySelectorAll('table.FR th').forEach(th => {
	// Exclude headers that are part of a colspan or rowspan and don't represent a direct sortable column
	if (th.hasAttribute('colspan') || th.hasAttribute('rowspan')) {
		const table = th.closest('table');
		if (table) {
		} else {
			// For other tables, if it has colspan/rowspan, don't make it sortable
			return;
		}
	}

	const table = th.closest('table');
	if (table && table.classList.contains('sortable')) {
		th.style.cursor = 'pointer'; // Indicate sortable
		th.addEventListener('click', (() => {
			const tableBody = table.querySelector('tbody');
			if (!tableBody) return;

			let columnIndex = th.cellIndex;


			const currentIsAsc = th.classList.contains('asc');

			// Remove sorting classes from all headers in this table
			table.querySelectorAll('th').forEach(header => {
				header.classList.remove('asc', 'desc');
			});

			// Sort the rows, explicitly targeting tbody rows
			let rowsToSort = Array.from(tableBody.querySelectorAll('tr:not([style*="display: none"])'));

			if (table.caption === 'Chunk Servers') {
				// Separate disconnected rows and regular rows
				const disconnectedRows = rowsToSort.filter(row => row.querySelector('td[colspan="12"]'));
				const regularRows = rowsToSort.filter(row => !row.querySelector('td[colspan="12"]'));

				regularRows.sort(comparer(columnIndex, !currentIsAsc));

				// Re-append disconnected rows (e.g., at the end)
				regularRows.forEach(tr => tableBody.appendChild(tr));
				disconnectedRows.forEach(tr => tableBody.appendChild(tr)); // Append disconnected rows at the end
			} else {
				rowsToSort.sort(comparer(columnIndex, !currentIsAsc))
					.forEach(tr => tableBody.appendChild(tr));
			}

			// Add sorting class to the clicked header
			th.classList.toggle('asc', !currentIsAsc);
			th.classList.toggle('desc', currentIsAsc);
		}));
	}
});
