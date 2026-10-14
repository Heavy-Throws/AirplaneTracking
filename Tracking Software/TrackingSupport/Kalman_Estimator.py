import numpy as np
import time

class TimeAdaptiveADSBLateralKF:
    def __init__(self, process_noise_sigma=0.05, measurement_noise=0.0001):
        """
        An adaptive 2D Constant Velocity Kalman Filter that adjusts to variable 
        and delayed timestamps from ADS-B telemetry.
        """
        self.sigma_q = process_noise_sigma  # Magnitude of acceleration noise
        self.R = np.eye(2) * measurement_noise
        
        self.H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0]
        ])
        
        self.P = np.eye(4) * 1.0
        self.x = np.zeros((4, 1))
        
        self.last_timestamp = None
        self.initialized = False

    def _rebuild_matrices(self, dt):
        """Dynamically builds F and Q matrices based on a specific dt interval."""
        F = np.array([
            [1.0, 0.0,  dt, 0.0],
            [0.0, 1.0, 0.0,  dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        
        dt2 = dt ** 2
        dt3 = dt ** 3
        dt4 = dt ** 4
        
        Q = np.array([
            [dt4/4,   0.0, dt3/2,   0.0],
            [  0.0, dt4/4,   0.0, dt3/2],
            [dt3/2,   0.0,   dt2,   0.0],
            [  0.0, dt3/2,   0.0,   dt2]
        ]) * (self.sigma_q ** 2)
        
        return F, Q

    def process_measurement(self, measured_lat, measured_lon, measurement_timestamp):
        """
        Executes both Predict and Update phases using the precise telemetry timestamp,
        updating the core filter tracking state.
        """
        if not self.initialized:
            self.x = np.array([[measured_lat], [measured_lon], [0.0], [0.0]])
            self.last_timestamp = measurement_timestamp
            self.initialized = True
            return self.x

        dt = measurement_timestamp - self.last_timestamp
        if dt <= 0:
            return self.x
            
        F, Q = self._rebuild_matrices(dt)

        # --- PREDICT STEP ---
        self.x = np.dot(F, self.x)
        self.P = np.dot(np.dot(F, self.P), F.T) + Q

        # --- UPDATE STEP ---
        z = np.array([[measured_lat], [measured_lon]])
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        
        self.x = self.x + np.dot(K, y)
        self.P = np.dot((np.eye(4) - np.dot(K, self.H)), self.P)

        self.last_timestamp = measurement_timestamp
        return self.x

    def predict_current(self, target_timestamp=time.time()):
        """
        Non-destructively projects the aircraft's position forward to a target 
        timestamp (e.g., current real-world clock time).
        
        Does NOT alter internal states (self.x, self.P), keeping them clean 
        for future incoming historical/delayed packets.
        """
        if not self.initialized:
            return None, None
            
        dt = target_timestamp - self.last_timestamp
        
        # If the target time is behind our last processed state, we can't extrapolate backwards safely
        if dt <= 0:
            return self.x.copy(), self.P.copy()
            
        # Temporarily reconstruct F and Q for extrapolation time step
        F, Q = self._rebuild_matrices(dt)
        
        # Extrapolate state and covariance forward without mutating class variables
        predicted_x = np.dot(F, self.x)
        predicted_P = np.dot(np.dot(F, self.P), F.T) + Q
        
        return predicted_x, predicted_P

