import axios from "axios";

const client = axios.create({ baseURL: "/api" });

export interface ResourceObject<T> {
  type: string;
  uid: string;
  attributes: T;
  relationships?: Record<string, { data: { type: string; uid: string } | null }>;
}

export interface JsonApiDocument<T> {
  data: ResourceObject<T> | ResourceObject<T>[];
  meta?: { count?: number };
  jsonapi: { version: string };
}

export function extractOne<T>(doc: JsonApiDocument<T>): T & { uid: string } {
  const resource = doc.data as ResourceObject<T>;
  return { uid: resource.uid, ...resource.attributes };
}

export function extractMany<T>(doc: JsonApiDocument<T>): (T & { uid: string })[] {
  const resources = doc.data as ResourceObject<T>[];
  return resources.map((r) => ({ uid: r.uid, ...r.attributes }));
}

export function extractOneWithRels<T>(doc: JsonApiDocument<T>): T & { uid: string } & Record<string, unknown> {
  const resource = doc.data as ResourceObject<T>;
  const rels: Record<string, unknown> = {};
  if (resource.relationships) {
    for (const [key, val] of Object.entries(resource.relationships)) {
      rels[`${key}_uid`] = val.data?.uid ?? null;
    }
  }
  return { uid: resource.uid, ...resource.attributes, ...rels };
}

export function extractManyWithRels<T>(doc: JsonApiDocument<T>): (T & { uid: string } & Record<string, unknown>)[] {
  const resources = doc.data as ResourceObject<T>[];
  return resources.map((resource) => {
    const rels: Record<string, unknown> = {};
    if (resource.relationships) {
      for (const [key, val] of Object.entries(resource.relationships)) {
        rels[`${key}_uid`] = val.data?.uid ?? null;
      }
    }
    return { uid: resource.uid, ...resource.attributes, ...rels };
  });
}

export interface Team {
  uid: string;
  name: string;
  is_own: boolean;
  home_color: string;
  away_color: string;
}

export interface Player {
  uid: string;
  jersey_number: number;
  name?: string;
  team_uid: string;
}

export interface Game {
  uid: string;
  name: string;
  date: string;
  status: "pending" | "processing" | "done" | "failed";
  own_team_uid: string;
  opponent_team_uid: string;
  own_team_color: string;
  opponent_team_color: string;
  duration_seconds: number;
  fps: number;
  file_count: number;
  is_archived: boolean;
}

export interface GameTeamStatsData {
  uid: string;
  score: number;
  possession_pct: number;
  team_uid: string;
}

export interface GamePlayerStatsData {
  uid: string;
  jersey_number: number | null;
  distance_covered_m: number;
  shot_attempts: number;
  shot_makes: number;
  passes_made: number;
  passes_received: number;
  possession_frames: number;
  team_uid: string;
  player_uid?: string;
}

export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface GameEventData {
  uid: string;
  type: string;
  frame: number;
  timestamp_sec: number;
  team_uid?: string;
  player_uid?: string;
  bbox?: BBox | null;
}

export interface GameFileData {
  uid: string;
  original_filename: string;
  position: number;
  size_bytes: number;
  url: string;
}

export interface GameStatsResponse {
  team_stats: GameTeamStatsData[];
  player_stats: GamePlayerStatsData[];
}

export const teamsApi = {
  list: async (isOwn: boolean): Promise<Team[]> => {
    const { data } = await client.get("/teams", { params: { is_own: isOwn } });
    return extractMany(data);
  },
  create: async (body: { name: string; is_own: boolean; home_color: string; away_color: string }): Promise<Team> => {
    const { data } = await client.post("/teams", {
      data: { type: "teams", attributes: body },
    });
    return extractOne(data);
  },
  update: async (uid: string, attrs: Partial<Omit<Team, "uid">>): Promise<Team> => {
    const { data } = await client.patch(`/teams/${uid}`, {
      data: { type: "teams", uid, attributes: attrs },
    });
    return extractOne(data);
  },
  delete: async (uid: string): Promise<void> => {
    await client.delete(`/teams/${uid}`);
  },
};

export const playersApi = {
  list: async (teamUid: string): Promise<Player[]> => {
    const { data } = await client.get("/players", { params: { team: teamUid } });
    return extractManyWithRels(data) as unknown as Player[];
  },
  create: async (body: { team_uid: string; jersey_number: number; name?: string }): Promise<Player> => {
    const { data } = await client.post("/players", {
      data: {
        type: "players",
        attributes: { jersey_number: body.jersey_number, name: body.name },
        relationships: {
          team: { data: { type: "teams", uid: body.team_uid } },
        },
      },
    });
    return extractOneWithRels(data) as unknown as Player;
  },
  delete: async (uid: string): Promise<void> => {
    await client.delete(`/players/${uid}`);
  },
};

export const gamesApi = {
  list: async (archived?: boolean): Promise<Game[]> => {
    const params: Record<string, string> = {};
    if (archived !== undefined) params.archived = String(archived);
    const { data } = await client.get("/games", { params });
    return extractManyWithRels(data) as unknown as Game[];
  },
  update: async (uid: string, attrs: Partial<Pick<Game, "is_archived">>): Promise<Game> => {
    const { data } = await client.patch(`/games/${uid}`, {
      data: { type: "games", uid, attributes: attrs },
    });
    return extractOneWithRels(data) as unknown as Game;
  },
  get: async (uid: string): Promise<Game> => {
    const { data } = await client.get(`/games/${uid}`);
    return extractOneWithRels(data) as unknown as Game;
  },
  upload: async (formData: FormData, onProgress?: (pct: number) => void): Promise<Game> => {
    const { data } = await client.post("/games", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
    return extractOneWithRels(data) as unknown as Game;
  },
  stats: async (uid: string): Promise<GameStatsResponse> => {
    const { data } = await client.get(`/games/${uid}/stats`);
    const raw = data.data;
    return {
      team_stats: raw.team_stats.map((r: ResourceObject<Record<string, unknown>>) => ({
        uid: r.uid,
        ...r.attributes,
        team_uid: r.relationships?.team?.data?.uid,
      })),
      player_stats: raw.player_stats.map((r: ResourceObject<Record<string, unknown>>) => ({
        uid: r.uid,
        ...r.attributes,
        team_uid: r.relationships?.team?.data?.uid,
        player_uid: r.relationships?.player?.data?.uid,
      })),
    };
  },
  files: async (uid: string): Promise<GameFileData[]> => {
    const { data } = await client.get(`/games/${uid}/files`);
    return extractMany(data) as unknown as GameFileData[];
  },
  events: async (uid: string, type?: string): Promise<GameEventData[]> => {
    const params: Record<string, string> = {};
    if (type) params.type = type;
    const { data } = await client.get(`/games/${uid}/events`, { params });
    const resources = data.data as ResourceObject<Record<string, unknown>>[];
    return resources.map((r) => ({
      uid: r.uid,
      ...r.attributes,
      team_uid: r.relationships?.team?.data?.uid,
      player_uid: r.relationships?.player?.data?.uid,
    })) as unknown as GameEventData[];
  },
};
