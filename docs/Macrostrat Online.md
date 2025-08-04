Macrostrat Online
=================

There are currently two non-development (non-test), publicly accessible
instances of the Macrostrat platform:

- v1: [macrostrat.org](https://macrostrat.org/)
- v2: [v2.macrostrat.org](https://v2.macrostrat.org/)

The v2 instance currently runs on a [Kubernetes](https://kubernetes.io/)
cluster. It uses [Flux](https://fluxcd.io/) to periodically poll a [private
GitHub repository](https://github.com/UW-Macrostrat/tiger-macrostrat-config)
for updated configuration and updates the cluster as necessary. Backend
storage is provided by a [Ceph](https://ceph.io/en/) cluster, which includes
an [object gateway](https://docs.ceph.com/en/quincy/radosgw/) that provides
an S3-compatible interface.
