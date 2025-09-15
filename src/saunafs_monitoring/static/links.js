/* Logic to manage navigation links on top of page */

function setHostAndPort(currentParams, newParams) {
	if (currentParams.has("masterhost")) {
		newParams.set("masterhost", currentParams.get("masterhost"));
	}
	if (currentParams.has("masterport")) {
		newParams.set("masterport", currentParams.get("masterport"));
	}
}

document.querySelectorAll('nav > a').forEach(link => {
	const params = new URLSearchParams(window.location.search);
	const url = new URL(link.href, window.location.origin); // Ensure absolute URL
	setHostAndPort(params, url.searchParams);

	const sectionStr = params.get("sections") || "";
	const sections = sectionStr.split("|");
	const urlSection = url.searchParams.get("sections");
	const sectionSelected = sections.indexOf(urlSection) !== -1;

	if (!sectionSelected) {
		const plus = document.createElement("a");
		plus.innerHTML = " +";
		plus.classList.add("selectSection");

		const plusUrl = new URL(url.toString());
		plusUrl.searchParams.set("sections", sectionStr + "|" + urlSection);
		plus.href = plusUrl.toString();

		link.appendChild(plus);

	} else if (sectionSelected && sections.length > 1) {
		const minus = document.createElement("a");
		minus.innerHTML = " -";
		minus.classList.add("selectSection");

		const minusUrl = new URL(url.toString());

		// Hacky way to remove redundant pipes but it works
		let newSection = sectionStr.replace(urlSection, "");
		newSection = newSection.replace("||", "|");
		if (newSection.charAt(0) === '|') {
			newSection = newSection.substring(1);
		}
		if (newSection.charAt(newSection.length - 1) === '|') {
			newSection = newSection.substring(0, newSection.length - 1);
		}

		minusUrl.searchParams.set("sections", newSection);
		minus.href = minusUrl.toString();
		link.appendChild(minus);
	}

	if (sectionSelected) {
		link.classList.add("active");
	}

	if (sectionSelected && sections.length === 1) {
		// Workaround to make the text align with no +/- sign
		link.classList.add("onlyActive");
	}

	link.href = url.toString();
});

document.querySelectorAll("a.DISCONNECTED").forEach(link => {
	link.addEventListener("click", function() {
		const current_params = new URLSearchParams(window.location.search);
		const params = new URLSearchParams();
		params.append("ip", link.dataset.ip);
		params.append("port", link.dataset.port);
		setHostAndPort(current_params, params);
		link.innerHTML = "...";
		link.style.cursor = "default";
		fetch(`/remove_chunkserver.cgi?${params}`, {
			method: "POST",
		})
			.then(response => {
				if (!response.ok) {
					link.innerHTML = "Disconnect";
					link.style.cursor = "pointer";
					alert("Could not remove chunkserver! Check logs");
				} else {
					link.closest("tr").remove();
				}
			})
			.catch(e => {
				console.error(e);
				link.innerHTML = "Disconnect";
				link.style.cursor = "pointer";
				alert("Could not remove chunkserver! Check JS console log");
			});
	});
});
