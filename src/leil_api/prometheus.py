# Copyright 2026 Urmas Rist <urmas@urist.ee>
#
# SaunaFS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# SaunaFS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SaunaFS  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
from typing import override
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from prometheus_client.registry import Collector

from leil_client import SaunaFSClient
from leil_client.models import Metric

leilfs_prometheus_metric_names = {
        "BYTES_RECEIVED_INCREMENT": ("received_bytes", "Amount of bytes received"),
        "BYTES_SEND_INCREMENT": ("sent_bytes", "Amount of bytes sent"),
        "NUMBER_OF_CHUNKS_GAUGE": ("chunks", "Number of chunks")
}

client_masterhost = os.getenv("SAUNAFS_MASTER_HOST", "sfsmaster")
client_port = int(os.getenv("SAUNAFS_MASTER_PORT", 9421))

class PrometheusMetric():
    name: str = ""
    help: str = ""
    type: str = ""
    labels: list[str] = []
    value: float = 0.0

def get_leil_metrics():
    client = SaunaFSClient(client_masterhost,
                              client_port)
    # TODO(Urist): Get chunkserver metrics as well when that's implemented
    return client.get_metrics(client.master_host,
                                 client.master_port)

def convert_to_prometheus(metrics: list[Metric], prefix: str) -> list[PrometheusMetric]:
    converted: list[PrometheusMetric] = []
    for metric in metrics:
        newMetric = PrometheusMetric()
        newMetric.name, newMetric.help = leilfs_prometheus_metric_names.get(metric.name, (metric.name, ""))
        newMetric.name = prefix + newMetric.name
        newMetric.name = newMetric.name.lower()

        if "INCREMENT" in metric.name:
            newMetric.type = "counter"
        elif "GAUGE" in metric.name:
            newMetric.type = "gauge"
        else:
            raise RuntimeError(f"Unknown metric type {metric.name}")

        newMetric.value = metric.value
        converted.append(newMetric)

    return converted


class LeilFSCollector(Collector):
    @override
    def collect(self):
        try:
            leil_metrics = get_leil_metrics()
            prom_metrics = convert_to_prometheus(leil_metrics, "lfsmaster_")
            for metric in prom_metrics:
                if metric.type == "gauge":
                    if len(metric.labels) != 0:
                        yield GaugeMetricFamily(name="", documentation=metric.help,
                                                value=metric.value, labels=metric.labels)
                    else:
                        yield GaugeMetricFamily(metric.name, metric.help,
                                                value=metric.value)
                elif metric.type == "counter":
                    if len(metric.labels) != 0:
                        yield CounterMetricFamily(name="", documentation=metric.help,
                                                value=metric.value, labels=metric.labels)
                    else:
                        yield CounterMetricFamily(metric.name, metric.help,
                                                value=metric.value)
        except (RuntimeError, ConnectionRefusedError) as e:
            logging.warning(f"Could not get prometheus metrics: {e}")
            return

def setup_prometheus():
    REGISTRY.register(LeilFSCollector())
