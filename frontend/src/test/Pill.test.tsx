import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Pill, hypothesisTone } from "@/components/ui/Pill";

describe("Pill", () => {
  it("renders children", () => {
    render(<Pill>BEAT</Pill>);
    expect(screen.getByText("BEAT")).toBeInTheDocument();
  });
  it("applies tone class for green", () => {
    const { container } = render(<Pill tone="green">+0.31</Pill>);
    expect(container.firstChild).toHaveClass("text-up");
  });
  it("applies amber class", () => {
    const { container } = render(<Pill tone="amber">MIXED</Pill>);
    expect(container.firstChild).toHaveClass("text-amber");
  });
});

describe("hypothesisTone", () => {
  it("maps labels to tones", () => {
    expect(hypothesisTone("BEAT")).toBe("green");
    expect(hypothesisTone("MISS")).toBe("red");
    expect(hypothesisTone("MIXED")).toBe("amber");
    expect(hypothesisTone(null)).toBe("default");
    expect(hypothesisTone("NO SIGNAL")).toBe("default");
  });
});
