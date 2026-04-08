import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the title", () => {
    render(<App />);
    expect(screen.getByText(/Next-Gen AI Agents/i)).toBeInTheDocument();
  });

  it("shows the input form", () => {
    render(<App />);
    expect(screen.getByLabelText(/input/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /invoke/i })).toBeInTheDocument();
  });
});
