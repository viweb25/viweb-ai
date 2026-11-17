import { get } from './client';

export type Template = { id: string; name: string; stage: string; config_schema: Record<string, unknown> };
export type Health = { status: string; service: string };

export function loadCatalogue(signal: AbortSignal): Promise<[Health, Template[]]> {
  return Promise.all([
    get<Health>('/health/live', signal),
    get<Template[]>('/api/v1/function-templates', signal),
  ]);
}
