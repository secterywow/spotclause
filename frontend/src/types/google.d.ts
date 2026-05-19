interface Window {
  google?: {
    accounts?: {
      id?: {
        initialize: (config: { client_id: string; use_fedcm_for_prompt?: boolean; callback: (response: { credential?: string }) => void }) => void
        prompt: (callback?: (notification: any) => void) => void
        renderButton: (element: HTMLElement, config: Record<string, any>) => void
      }
      oauth2?: {
        initTokenClient: (config: Record<string, any>) => { requestAccessToken: () => void }
      }
    }
  }
}
