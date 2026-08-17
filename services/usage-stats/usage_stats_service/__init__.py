"""Usage-stats worker service.

A thin frontend over `macrostrat.usage_stats_capture`: reads configuration from
the environment and runs the harvester. Deployed as a Kubernetes CronJob.
"""
