// TDD RED — written before implementation
import React from "react";
import { render, screen } from "@testing-library/react-native";
import { EnergySliders } from "../components/EnergySliders";

const DEFAULT_VALUES = { sleep_quality: 3, mood: 3, energy_level: 3 };
const noop = jest.fn();

describe("EnergySliders", () => {
  test("renders Sleep label", () => {
    render(<EnergySliders values={DEFAULT_VALUES} onChange={noop} />);
    expect(screen.getByText("Sleep")).toBeTruthy();
  });

  test("renders Mood label", () => {
    render(<EnergySliders values={DEFAULT_VALUES} onChange={noop} />);
    expect(screen.getByText("Mood")).toBeTruthy();
  });

  test("renders Energy label", () => {
    render(<EnergySliders values={DEFAULT_VALUES} onChange={noop} />);
    expect(screen.getByText("Energy")).toBeTruthy();
  });

  test("displays current values", () => {
    render(<EnergySliders values={{ sleep_quality: 2, mood: 4, energy_level: 5 }} onChange={noop} />);
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
  });

  test("renders with min value of 1", () => {
    render(<EnergySliders values={{ sleep_quality: 1, mood: 1, energy_level: 1 }} onChange={noop} />);
    const ones = screen.getAllByText("1");
    expect(ones.length).toBeGreaterThanOrEqual(3);
  });

  test("renders with max value of 5", () => {
    render(<EnergySliders values={{ sleep_quality: 5, mood: 5, energy_level: 5 }} onChange={noop} />);
    const fives = screen.getAllByText("5");
    expect(fives.length).toBeGreaterThanOrEqual(3);
  });
});
