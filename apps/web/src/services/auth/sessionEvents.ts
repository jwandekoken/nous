type SessionExpiredListener = (message?: string) => void;

const sessionExpiredListeners = new Set<SessionExpiredListener>();

export const onSessionExpired = (listener: SessionExpiredListener) => {
  sessionExpiredListeners.add(listener);

  return () => {
    sessionExpiredListeners.delete(listener);
  };
};

export const emitSessionExpired = (message?: string) => {
  sessionExpiredListeners.forEach((listener) => {
    try {
      listener(message);
    } catch (error) {
      console.error("Session expired listener failed", error);
    }
  });
};
