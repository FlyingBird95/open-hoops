import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { ScoreCard } from "./score-card";

afterEach(cleanup);

const defaultProps = {
  homeTeam: "Bulls",
  awayTeam: "Lakers",
  homeScore: 98,
  awayScore: 102,
  homeColor: "#CE1141",
  awayColor: "#552583",
  homePossession: 0.55,
  awayPossession: 0.45,
};

describe("ScoreCard", () => {
  it("renders team names", () => {
    const { container } = render(<ScoreCard {...defaultProps} />);
    expect(container.textContent).toContain("Bulls");
    expect(container.textContent).toContain("Lakers");
  });

  it("renders scores", () => {
    const { container } = render(<ScoreCard {...defaultProps} />);
    const scores = container.querySelectorAll(".text-4xl");
    expect(scores[0].textContent).toBe("98");
    expect(scores[1].textContent).toBe("102");
  });

  it("applies team colors to color swatches", () => {
    const { container } = render(<ScoreCard {...defaultProps} />);
    const swatches = container.querySelectorAll(".rounded-full[style]") as NodeListOf<HTMLElement>;
    expect(swatches[0].style.backgroundColor).toBe("rgb(206, 17, 65)");
    expect(swatches[1].style.backgroundColor).toBe("rgb(85, 37, 131)");
  });

  it("displays possession percentages rounded from decimals", () => {
    const { container } = render(<ScoreCard {...defaultProps} />);
    expect(container.textContent).toContain("55%");
    expect(container.textContent).toContain("45%");
  });

  it("rounds possession percentages correctly", () => {
    const { container } = render(
      <ScoreCard {...defaultProps} homePossession={0.333} awayPossession={0.667} />
    );
    expect(container.textContent).toContain("33%");
    expect(container.textContent).toContain("67%");
  });

  it("possession bar widths match values", () => {
    const { container } = render(<ScoreCard {...defaultProps} />);
    const bars = container.querySelectorAll(".h-2 .h-full") as NodeListOf<HTMLElement>;
    expect(parseFloat(bars[0].style.width)).toBeCloseTo(55, 0);
    expect(parseFloat(bars[1].style.width)).toBeCloseTo(45, 0);
  });

  it("handles 0% / 100% possession edge case", () => {
    const { container } = render(
      <ScoreCard {...defaultProps} homePossession={0} awayPossession={1} />
    );
    expect(container.textContent).toContain("0%");
    expect(container.textContent).toContain("100%");
    const bars = container.querySelectorAll(".h-2 .h-full") as NodeListOf<HTMLElement>;
    expect(bars[0].style.width).toBe("0%");
    expect(bars[1].style.width).toBe("100%");
  });
});
