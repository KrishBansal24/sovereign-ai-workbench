# Python Sandbox

To support complex analysis, transformation, and custom artifact generation that cannot be solved by static backend logic, the Sovereign AI Workbench includes a safe Python Sandbox.

## Execution Model

The `SandboxService` provides a bounded environment for executing generated Python code. 

- **Isolation:** Code execution happens in a dedicated subprocess. A temporary workspace directory is created for the execution and populated with any requested input data (e.g., CSV files). After execution, the workspace and any generated temporary files are completely purged.
- **Timeout Restrictions:** Code execution is strictly bounded by a timeout (e.g., 5 seconds) to prevent infinite loops or resource exhaustion on the host machine.
- **No Arbitrary Shell:** The sandbox only executes Python code via the `subprocess` module. Arbitrary shell commands (`shell=True`) are strictly forbidden by the execution engine.
- **Output Capture:** Standard output (`stdout`) and standard error (`stderr`) are captured and sanitized before being returned to the TUI or the Agent.
- **Safe Failure State:** If the code fails due to a timeout or syntax error, the backend recovers gracefully, cleans up the workspace, and returns a structured failure observation to the caller.

## Security Note
This implementation provides process and workspace isolation suitable for bounded AI tasks. It does *not* claim to be a hardened, military-grade virtual machine or container boundary (Phase 8 functionality). It is designed to prevent runaway code and accidental namespace corruption during standard industrial analysis workflows.
