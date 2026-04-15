const WaveSurferMock = {
  create: () => ({
    destroy: jest.fn(),
    load: jest.fn(),
    on: jest.fn(),
    pause: jest.fn(),
    play: jest.fn(),
    setVolume: jest.fn(),
  }),
}
export default WaveSurferMock
