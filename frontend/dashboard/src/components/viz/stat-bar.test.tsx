import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { StatBar } from "./stat-bar";

describe("StatBar", () => {
  it("renders bar with correct percentage width", () => {
    const { container } = render(<StatBar value={50} max={100} color="#f00" />);
    const bar = container.querySelector("[style]") as HTMLElement;
    expect(bar.style.width).toBe("50%");
  });

  it("renders 0% when max is 0", () => {
    const { container } = render(<StatBar value={5} max={0} color="#f00" />);
    const bar = container.querySelector("[style]") as HTMLElement;
    expect(bar.style.width).toBe("0%");
  });

  it("renders 100% when value equals max", () => {
    const { container } = render(<StatBar value={10} max={10} color="#0f0" />);
    const bar = container.querySelector("[style]") as HTMLElement;
    expect(bar.style.width).toBe("100%");
  });

  it("applies custom color", () => {
    const { container } = render(<StatBar value={3} max={10} color="#abc" />);
    const bar = container.querySelector("[style]") as HTMLElement;
    expect(bar.style.backgroundColor).toBe("rgb(170, 187, 204)");
  });

  it("applies additional className", () => {
    const { container } = render(<StatBar value={5} max={10} className="mt-4" />);
    expect(container.firstElementChild).toHaveClass("mt-4");
  });
});
