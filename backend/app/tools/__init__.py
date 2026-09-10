"""Controlled local tools and validation boundaries for the Phase 5 agent.

The package implements a fixed execution path: an untrusted tool request is
looked up in the registry, validated against its schema, policy-checked, run
through a named local implementation, and returned as a structured result.
"""
