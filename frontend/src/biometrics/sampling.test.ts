import { describe, expect, it } from "vitest";

import { pickShots, spread } from "./sampling";

const shots = (n: number) => Array.from({ length: n }, (_, i) => ({ item: i, at: i * 100 }));

describe("spread", () => {
  it("keeps first and last element", () => {
    expect(spread([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 4)).toEqual([0, 3, 6, 9]);
    expect(spread([1, 2], 5)).toEqual([1, 2]);
  });
});

describe("pickShots", () => {
  it("keeps everything when under the limit", () => {
    expect(pickShots(shots(5), null, 10, 500)).toEqual([0, 1, 2, 3, 4]);
  });

  it("samples the whole step when the movement was not detected", () => {
    const picked = pickShots(shots(23), null, 10, 500);
    expect(picked).toHaveLength(10);
    expect(picked[0]).toBe(0);
    expect(picked.at(-1)).toBe(22);
  });

  it("keeps the frames around the detected movement even if the head returned", () => {
    const picked = pickShots(shots(23), 900, 10, 500);
    expect(picked).toHaveLength(10);
    expect(picked).toEqual(expect.arrayContaining([4, 5, 6, 7, 8, 9]));
  });
});
