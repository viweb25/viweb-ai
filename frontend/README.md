# Frontend

From the repository root, run with Node 22:

```bash
npm ci
npm run dev
```

Open http://127.0.0.1:3000. The alternative is
`docker compose --profile frontend up -d --build frontend`.

## Dashboard

- **Overview** counts inspection responses in the current browser session.
- **Inspection** sends a camera frame or uploaded image and an acceptance rule to inference.
- **Training examples** reads and writes labeled examples through the business API.
- **Function catalogue** displays templates returned by the business API.
- **Preferences** uses `src/context/WorkspacePreferences.tsx` for the workspace display name
  and acceptance rule. Preferences are stored in this browser. The display name is
  presentation only. Company identity and authorisation belong to the backend.

## API modules

`src/services/api/client.ts` handles JSON and API errors. The feature modules
`inspection.ts`, `trainingExamples.ts`, `catalogue.ts`, and `health.ts` own their
endpoints and response types. Vite proxies requests to the backend and inference service.
See `vite.config.ts` for targets. Keep secrets out of VITE-prefixed environment variables.

Run `npm run typecheck` and `npm run build` from the repository root before merging.

For the dashboard's owner account setup, see the
[sign-in guide](../docs/guides/SIGN_IN.md).

## Camera connections

In **Inspection → Image source**, select a camera and click **Start camera**. Grant
camera permission if prompted. Some browsers reveal device names only after you
grant permission. Stop the current camera to select another, then start it.

- Connect USB cameras and HDMI capture adapters to the computer running the dashboard.
  If the operating system and browser expose the device as a camera, it appears in the list.
- For a phone or tablet, open the dashboard on that device over HTTPS and select its
  camera. The local development address binds to the laptop and is for use on that
  laptop. You can also use **Take a photo** on a supported mobile browser or upload a saved photo.
- For CCTV, NVR, or industrial Ethernet cameras, open the vendor viewer on the
  dashboard computer. In a desktop browser that supports window or tab capture, use
  **Share camera viewer**, select only the viewer, and click
  **Capture frame**. To feed raw RTSP or a vendor SDK directly, a camera-specific edge
  adapter is needed. The browser picker lists locally exposed devices.

Use **Capture frame** before inspecting or labeling. Camera and viewer preview run
in the browser. The inspection API receives the JPEG you submit.
