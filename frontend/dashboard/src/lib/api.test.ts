import { describe, it, expect } from "vitest";
import {
  extractOne,
  extractMany,
  extractOneWithRels,
  extractManyWithRels,
  type JsonApiDocument,
} from "./api";

describe("extractOne", () => {
  it("extracts uid and attributes from single resource", () => {
    const doc: JsonApiDocument<{ name: string }> = {
      data: { type: "teams", uid: "abc123", attributes: { name: "Lakers" } },
      jsonapi: { version: "1.0" },
    };
    expect(extractOne(doc)).toEqual({ uid: "abc123", name: "Lakers" });
  });

  it("spreads all attributes", () => {
    const doc: JsonApiDocument<{ name: string; score: number }> = {
      data: { type: "stats", uid: "x1", attributes: { name: "Q1", score: 42 } },
      jsonapi: { version: "1.0" },
    };
    const result = extractOne(doc);
    expect(result.uid).toBe("x1");
    expect(result.name).toBe("Q1");
    expect(result.score).toBe(42);
  });
});

describe("extractMany", () => {
  it("extracts array of resources", () => {
    const doc: JsonApiDocument<{ name: string }> = {
      data: [
        { type: "teams", uid: "a1", attributes: { name: "Team A" } },
        { type: "teams", uid: "b2", attributes: { name: "Team B" } },
      ],
      jsonapi: { version: "1.0" },
    };
    const result = extractMany(doc);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ uid: "a1", name: "Team A" });
    expect(result[1]).toEqual({ uid: "b2", name: "Team B" });
  });

  it("handles empty array", () => {
    const doc: JsonApiDocument<{ name: string }> = {
      data: [],
      jsonapi: { version: "1.0" },
    };
    expect(extractMany(doc)).toEqual([]);
  });
});

describe("extractOneWithRels", () => {
  it("extracts relationships as _uid suffixed keys", () => {
    const doc: JsonApiDocument<{ jersey_number: number }> = {
      data: {
        type: "players",
        uid: "p1",
        attributes: { jersey_number: 23 },
        relationships: {
          team: { data: { type: "teams", uid: "t1" } },
        },
      },
      jsonapi: { version: "1.0" },
    };
    const result = extractOneWithRels(doc);
    expect(result.uid).toBe("p1");
    expect(result.jersey_number).toBe(23);
    expect(result.team_uid).toBe("t1");
  });

  it("handles null relationship", () => {
    const doc: JsonApiDocument<{ name: string }> = {
      data: {
        type: "games",
        uid: "g1",
        attributes: { name: "Game 1" },
        relationships: {
          winner: { data: null },
        },
      },
      jsonapi: { version: "1.0" },
    };
    const result = extractOneWithRels(doc);
    expect(result.winner_uid).toBeNull();
  });

  it("works without relationships key", () => {
    const doc: JsonApiDocument<{ name: string }> = {
      data: { type: "teams", uid: "t1", attributes: { name: "X" } },
      jsonapi: { version: "1.0" },
    };
    const result = extractOneWithRels(doc);
    expect(result).toEqual({ uid: "t1", name: "X" });
  });
});

describe("extractManyWithRels", () => {
  it("extracts array with relationships", () => {
    const doc: JsonApiDocument<{ jersey_number: number }> = {
      data: [
        {
          type: "players",
          uid: "p1",
          attributes: { jersey_number: 10 },
          relationships: { team: { data: { type: "teams", uid: "t1" } } },
        },
        {
          type: "players",
          uid: "p2",
          attributes: { jersey_number: 5 },
          relationships: { team: { data: { type: "teams", uid: "t2" } } },
        },
      ],
      jsonapi: { version: "1.0" },
    };
    const result = extractManyWithRels(doc);
    expect(result).toHaveLength(2);
    expect(result[0].team_uid).toBe("t1");
    expect(result[1].team_uid).toBe("t2");
  });
});
