import { useEffect, useState } from 'react';

import { loadCatalogue, type Template } from './services/api/catalogue';

export function App() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [status, setStatus] = useState('Connecting to API…');
  useEffect(() => {
    const controller = new AbortController();
    loadCatalogue(controller.signal).then(([, items]) => { setTemplates(items); setStatus('API connected'); })
      .catch((error: Error) => {
        if (error.name !== 'AbortError') setStatus('API unavailable. Start the backend stack and refresh.');
      });
    return () => controller.abort();
  }, []);
  return <main>
    <header><span>VI / WEBSYNC</span><small>Development workspace · Phase 0</small></header>
    <p className="eyebrow">INDUSTRIAL AI PLATFORM</p>
    <h1>One platform.<br/>Independent AI functions.</h1>
    <p className="intro">Configure, teach, validate and deploy inspection functions.
      This foundation connects the web shell to the API; customer workflows are still to be built.</p>
    <p role="status" className="status">{status}</p>
    <section aria-labelledby="catalogue"><h2>Function roadmap</h2>
      <div className="grid">{templates.map(item => <article key={item.id}>
        <small>{item.stage.replace('planned: ', '')}</small><h3>{item.name}</h3>
        <p>Planned · model and workflow not enabled</p>
      </article>)}</div>
    </section>
    <footer>Hemachandran · Web / Siva · Platform / Akash · AI &amp; Integration</footer>
  </main>;
}
