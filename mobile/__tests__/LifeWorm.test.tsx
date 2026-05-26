// TDD RED — written before implementation
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react-native";
import { LifeWorm } from "../components/LifeWorm";

jest.useFakeTimers();

describe("LifeWorm", () => {
  afterEach(() => {
    jest.clearAllTimers();
  });

  test("renders initial elapsed time as 00:00", () => {
    render(<LifeWorm durationMinutes={25} />);
    expect(screen.getByText("00:00")).toBeTruthy();
  });

  test("shows Start button when not yet started", () => {
    render(<LifeWorm durationMinutes={25} />);
    expect(screen.getByText("Start")).toBeTruthy();
  });

  test("shows Pause button after pressing Start", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    expect(screen.getByText("Pause")).toBeTruthy();
  });

  test("time advances by 1 second after interval fires", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(1000); });
    expect(screen.getByText("00:01")).toBeTruthy();
  });

  test("time advances to 01:00 after 60 seconds", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(60_000); });
    expect(screen.getByText("01:00")).toBeTruthy();
  });

  test("pausing stops time from advancing", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(3000); });
    fireEvent.press(screen.getByText("Pause"));
    act(() => { jest.advanceTimersByTime(5000); });
    expect(screen.getByText("00:03")).toBeTruthy();
  });

  test("shows Resume after pausing with elapsed time", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(1000); });
    fireEvent.press(screen.getByText("Pause"));
    expect(screen.getByText("Resume")).toBeTruthy();
  });

  test("Reset button appears after first tick", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(1000); });
    fireEvent.press(screen.getByText("Pause"));
    expect(screen.getByText("Reset")).toBeTruthy();
  });

  test("Reset resets time to 00:00 and shows Start", () => {
    render(<LifeWorm durationMinutes={25} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(5000); });
    fireEvent.press(screen.getByText("Pause"));
    fireEvent.press(screen.getByText("Reset"));
    expect(screen.getByText("00:00")).toBeTruthy();
    expect(screen.getByText("Start")).toBeTruthy();
  });

  test("calls onComplete when duration is reached", () => {
    const onComplete = jest.fn();
    // 1 second duration (0.016... minutes)
    render(<LifeWorm durationMinutes={1 / 60} onComplete={onComplete} />);
    fireEvent.press(screen.getByText("Start"));
    act(() => { jest.advanceTimersByTime(2000); });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
