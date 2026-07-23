# Project Requirements Context

This folder keeps project-level context extracted from the source PDFs so the database redesign can be discussed with the scientific, technical, and delivery goals in view.

## High-Level Summary

The project is a system for monitoring human exposure to electric fields in indoor environments with high IoT-device density. It combines SDR-based spectrum sensing, edge processing, machine learning, cooperative thresholding, heat-map generation, and reporting against exposure regulations.

The database should support:

- sensor/device inventory and physical placement;
- SDR acquisition configuration;
- spectral measurements and derived metrics;
- sensor health/status telemetry;
- campaign planning and campaign/sensor assignment;
- AI/thresholding outputs and alert history;
- compliance report caching/export;
- users, audit logs, and system configuration.

legacy/ folder reflects the later project
