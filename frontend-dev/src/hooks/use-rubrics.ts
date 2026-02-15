import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import api from "@/lib/api";

export type RubricCriterion = {
  name: string;
  weight: number;
  levels: string[];
};

export type RubricContent = {
  levels: string[];
  criteria: RubricCriterion[];
};

export type Rubric = {
  id: string;
  name: string;
  createdById: string;
  content: RubricContent;
  createdAt: string;
};

export type CreateRubricInput = {
  name: string;
  content: RubricContent;
};

export type UpdateRubricInput = {
  name?: string;
  content?: RubricContent;
};

export type GenerateRubricInput = {
  instruction: string;
};

export type GenerateRubricOutput = {
  content: RubricContent;
};

export const rubricsKeys = {
  all: ["rubrics"] as const,
  lists: () => [...rubricsKeys.all, "list"] as const,
  list: () => [...rubricsKeys.lists()] as const,
  details: () => [...rubricsKeys.all, "detail"] as const,
  detail: (id: string) => [...rubricsKeys.details(), id] as const,
};

const fetchRubrics = async (): Promise<Rubric[]> => {
  const response = await api.get("/rubrics");
  return response.data;
};

const fetchRubric = async (id: string): Promise<Rubric> => {
  const response = await api.get(`/rubrics/${id}`);
  return response.data;
};

const createRubric = async (data: CreateRubricInput): Promise<Rubric> => {
  const response = await api.post("/rubrics", data);
  return response.data;
};

const updateRubric = async (id: string, data: UpdateRubricInput): Promise<Rubric> => {
  const response = await api.put(`/rubrics/${id}`, data);
  return response.data;
};

const deleteRubric = async (id: string): Promise<void> => {
  await api.delete(`/rubrics/${id}`);
};

const generateRubric = async (
  data: GenerateRubricInput,
): Promise<GenerateRubricOutput> => {
  const response = await api.post("/rubrics/generate", data);
  return response.data;
};

export function useRubrics(enabled = true) {
  return useQuery({
    queryKey: rubricsKeys.list(),
    queryFn: fetchRubrics,
    enabled,
  });
}

export function useRubric(id?: string, enabled = true) {
  return useQuery({
    queryKey: id ? rubricsKeys.detail(id) : rubricsKeys.detail("unknown"),
    queryFn: () => fetchRubric(id as string),
    enabled: enabled && !!id,
  });
}

export function useCreateRubric() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateRubricInput) => createRubric(data),
    onSuccess: (rubric) => {
      queryClient.invalidateQueries({ queryKey: rubricsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: rubricsKeys.detail(rubric.id) });
      toast.success("Rubric created successfully", { description: rubric.name });
    },
    onError: (error: Error) => {
      toast.error("Failed to create rubric", {
        description: error.message || "Something went wrong",
      });
    },
  });
}

export function useUpdateRubric() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateRubricInput }) =>
      updateRubric(id, data),
    onSuccess: (rubric) => {
      queryClient.invalidateQueries({ queryKey: rubricsKeys.detail(rubric.id) });
      queryClient.invalidateQueries({ queryKey: rubricsKeys.lists() });
      toast.success("Rubric updated successfully", { description: rubric.name });
    },
    onError: (error: Error) => {
      toast.error("Failed to update rubric", {
        description: error.message || "Something went wrong",
      });
    },
  });
}

export function useDeleteRubric() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteRubric(id),
    onSuccess: (_void, id) => {
      queryClient.invalidateQueries({ queryKey: rubricsKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: rubricsKeys.lists() });
      toast.success("Rubric deleted successfully");
    },
    onError: (error: Error) => {
      toast.error("Failed to delete rubric", {
        description: error.message || "Something went wrong",
      });
    },
  });
}

export function useGenerateRubric() {
  return useMutation({
    mutationFn: (data: GenerateRubricInput) => generateRubric(data),
    onError: (error: Error) => {
      toast.error("Failed to generate rubric", {
        description: error.message || "Something went wrong",
      });
    },
  });
}
