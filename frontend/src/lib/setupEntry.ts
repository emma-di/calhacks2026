export const SETUP_COMPLETE_KEY = 'aware-setup-complete-v1';
export function initialView(search: string, completed: boolean): 'live'|'preferences'|'log' {
  const requested=new URLSearchParams(search).get('view');
  if(requested==='preferences'||requested==='log'||requested==='live')return requested;
  return completed?'live':'preferences';
}
