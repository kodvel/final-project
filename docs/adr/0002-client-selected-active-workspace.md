# ADR 0002: Client-selected active workspace

The MVP has no authentication or server-side user session, so the active workspace is selected by the client UI and sent explicitly as `workspace_id` on scoped API requests. We rejected a global server-side `workspace.is_active` flag because one browser switching workspace would unexpectedly affect another browser or developer during the demo.
