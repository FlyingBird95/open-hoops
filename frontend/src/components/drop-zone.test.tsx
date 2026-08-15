import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DropZone } from "./drop-zone";

describe("DropZone", () => {
  it("renders upload prompt when no files", () => {
    render(<DropZone files={[]} onChange={() => {}} />);
    expect(screen.getByText(/drag videos here/i)).toBeInTheDocument();
  });

  it("displays file names when files present", () => {
    const files = [
      new File(["content"], "game1.mp4", { type: "video/mp4" }),
      new File(["content"], "game2.mp4", { type: "video/mp4" }),
    ];
    render(<DropZone files={files} onChange={() => {}} />);
    expect(screen.getByText("game1.mp4")).toBeInTheDocument();
    expect(screen.getByText("game2.mp4")).toBeInTheDocument();
  });

  it("calls onChange when remove button clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const files = [
      new File(["a"], "vid.mp4", { type: "video/mp4" }),
    ];
    const { container } = render(<DropZone files={files} onChange={onChange} />);

    const removeBtn = container.querySelector("button") as HTMLElement;
    await user.click(removeBtn);
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("formats file size in KB", () => {
    const file = new File(["x".repeat(512)], "small.mp4", { type: "video/mp4" });
    Object.defineProperty(file, "size", { value: 500 * 1024 });
    render(<DropZone files={[file]} onChange={() => {}} />);
    expect(screen.getByText("500 KB")).toBeInTheDocument();
  });

  it("formats file size in MB", () => {
    const file = new File(["x"], "big.mp4", { type: "video/mp4" });
    Object.defineProperty(file, "size", { value: 2.5 * 1024 * 1024 });
    render(<DropZone files={[file]} onChange={() => {}} />);
    expect(screen.getByText("2.5 MB")).toBeInTheDocument();
  });

  it("applies disabled state", () => {
    const { container } = render(<DropZone files={[]} onChange={() => {}} disabled />);
    const input = container.querySelector("input[type=file]") as HTMLInputElement;
    expect(input).toBeDisabled();
  });
});
