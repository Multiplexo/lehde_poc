import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type DiscrepancyUpdate, type DocumentUpdate, type Project, type Question } from '@/lib/api'

export const projectKeys = {
  all: ['projects'] as const,
  detail: (id: string) => ['projects', id] as const,
  onepager: (id: string) => ['projects', id, 'onepager'] as const,
  pages: (projectId: string, documentId: string) => ['projects', projectId, 'pages', documentId] as const,
}

export function useProjects() {
  return useQuery({ queryKey: projectKeys.all, queryFn: api.listProjects })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => api.getProject(id),
    // Poll while the analysis runs in the background.
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? 1500 : false),
  })
}

export function useDocumentPages(projectId: string, documentId: string | undefined) {
  return useQuery({
    queryKey: projectKeys.pages(projectId, documentId ?? ''),
    queryFn: () => api.getPages(projectId, documentId!),
    enabled: !!documentId,
    staleTime: Infinity,
  })
}

export function useOnepager(projectId: string, version: string | undefined) {
  return useQuery({
    queryKey: [...projectKeys.onepager(projectId), version],
    queryFn: () => api.getOnepager(projectId),
    enabled: !!version,
  })
}

function useProjectMutation<Variables>(projectId: string, mutate: (variables: Variables) => Promise<Project>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: mutate,
    onSuccess: (project) => {
      client.setQueryData(projectKeys.detail(projectId), project)
      void client.invalidateQueries({ queryKey: projectKeys.all, exact: true })
    },
  })
}

export function useStartAnalysis(projectId: string) {
  return useProjectMutation(projectId, () => api.startAnalysis(projectId))
}

export function useUpdateDocument(projectId: string) {
  return useProjectMutation(projectId, ({ documentId, data }: { documentId: string; data: DocumentUpdate }) =>
    api.updateDocument(projectId, documentId, data))
}

export function useUpdateDiscrepancy(projectId: string) {
  return useProjectMutation(projectId, ({ id, data }: { id: string; data: DiscrepancyUpdate }) =>
    api.updateDiscrepancy(projectId, id, data))
}

export function useUpdateQuestions(projectId: string) {
  return useProjectMutation(projectId, (questions: Question[]) => api.updateQuestions(projectId, questions))
}

export function useDeleteDocument(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => api.deleteDocument(projectId, documentId),
    onSuccess: () => client.invalidateQueries({ queryKey: projectKeys.detail(projectId) }),
  })
}

export function useCreateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.createProject,
    onSuccess: () => client.invalidateQueries({ queryKey: projectKeys.all }),
  })
}

export function useDeleteProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.deleteProject,
    onSuccess: () => client.invalidateQueries({ queryKey: projectKeys.all }),
  })
}
