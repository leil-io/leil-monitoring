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
	if (!cell) {
		return ''; // Return empty string if cell is undefined
	}
	// Handle humanized bytes (e.g., 1.23 MiB) by converting to a comparable number
	const humanizedBytesRegex = /^([\d\.]+) (B|KiB|MiB|GiB|TiB|PiB)$/;
	const text = cell.innerText || cell.textContent;
	const match = text.match(humanizedBytesRegex);

	if (match) {
		const value = parseFloat(match[1]);
		const unit = match[2];
		switch (unit) {
			case 'B': return value;
			case 'KiB': return value * 1024;
			case 'MiB': return value * 1024 * 1024;
			case 'GiB': return value * 1024 * 1024 * 1024;
			case 'TiB': return value * 1024 * 1024 * 1024 * 1024;
			case 'PiB': return value * 1024 * 1024 * 1024 * 1024 * 1024;
		}
	}

	// Try to parse as number, otherwise return as string
	return isNaN(Number(text)) ? text : Number(text);
}

function comparer(idx, asc) {
	return function(a, b) {
		const v1 = getCellValue(asc ? a : b, idx);
		const v2 = getCellValue(asc ? b : a, idx);
		return v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2);
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
