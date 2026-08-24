import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DonutChart } from "./donut-chart";

describe("DonutChart", () => {
  it("renders empty placeholder when total is zero", () => {
    const { container } = render(<DonutChart makes={0} misses={0} color="#f00" />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("renders SVG with percentage text", () => {
    render(<DonutChart makes={3} misses={7} color="#00f" />);
    expect(screen.getByText("30%")).toBeInTheDocument();
  });

  it("shows 100% when all makes", () => {
    render(<DonutChart makes={5} misses={0} color="#0f0" />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("shows 0% when all misses", () => {
    render(<DonutChart makes={0} misses={5} color="#0f0" />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("renders at custom size", () => {
    const { container } = render(<DonutChart makes={1} misses={1} color="#f00" size={96} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "96");
    expect(svg).toHaveAttribute("height", "96");
  });

  it("rounds percentage to nearest integer", () => {
    render(<DonutChart makes={1} misses={2} color="#f00" />);
    expect(screen.getByText("33%")).toBeInTheDocument();
  });
});
