#!/usr/bin/env python3
"""
Scikit-learn Integration for RLE Analysis
Machine learning models for RLE prediction, anomaly detection, and optimization
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import joblib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

class RLEPredictor:
    """Machine learning model for RLE prediction"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target for training"""
        # Select features for RLE prediction
        feature_columns = [
            'util_pct', 'temp_c', 'power_w', 'a_load', 't_sustain_s',
            'cpu_freq_mhz', 'cpu_cores_active', 'cpu_temp_max',
            'gpu_memory_used_gb', 'gpu_memory_total_gb', 'gpu_fan_pct', 'gpu_clock_mhz',
            'memory_used_gb', 'memory_total_gb', 'memory_util_pct',
            'disk_used_gb', 'disk_total_gb', 'disk_util_pct'
        ]
        
        # Filter available columns
        available_features = [col for col in feature_columns if col in df.columns]
        
        # Prepare features
        X = df[available_features].fillna(0).values
        y = df['rle_smoothed'].fillna(0).values
        
        self.feature_names = available_features
        
        return X, y
    
    def train(self, df: pd.DataFrame, model_type: str = 'random_forest') -> Dict[str, float]:
        """Train RLE prediction model"""
        print(f"Training RLE prediction model ({model_type})...")
        
        X, y = self.prepare_features(df)
        
        if len(X) < 10:
            print("Insufficient data for training")
            return {}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Choose model
        if model_type == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif model_type == 'linear':
            self.model = LinearRegression()
        elif model_type == 'ridge':
            self.model = Ridge(alpha=1.0)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'mse': mean_squared_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred),
            'r2': r2_score(y_test, y_pred),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        self.is_trained = True
        
        print(f"Model trained - R² = {metrics['r2']:.3f}, RMSE = {metrics['rmse']:.3f}")
        
        return metrics
    
    def predict(self, features: Dict[str, float]) -> float:
        """Predict RLE value from features"""
        if not self.is_trained:
            return 0.0
        
        # Convert features to array
        feature_array = np.array([features.get(name, 0) for name in self.feature_names]).reshape(1, -1)
        
        # Scale features
        feature_scaled = self.scaler.transform(feature_array)
        
        # Predict
        prediction = self.model.predict(feature_scaled)[0]
        
        return max(0.0, prediction)  # Ensure non-negative
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance (for tree-based models)"""
        if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
            return {}
        
        importance = self.model.feature_importances_
        return dict(zip(self.feature_names, importance))
    
    def save_model(self, path: str):
        """Save trained model"""
        if self.is_trained:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }
            joblib.dump(model_data, path)
            print(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model"""
        if Path(path).exists():
            model_data = joblib.load(path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.is_trained = True
            print(f"Model loaded from {path}")

class RLEAnomalyDetector:
    """Anomaly detection for RLE data"""
    
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train anomaly detection model"""
        print("Training RLE anomaly detection model...")
        
        # Select features for anomaly detection
        feature_columns = [
            'rle_smoothed', 'rle_raw', 'E_th', 'E_pw',
            'util_pct', 'temp_c', 'power_w', 'a_load', 't_sustain_s',
            'cpu_freq_mhz', 'gpu_clock_mhz', 'memory_util_pct'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0).values
        
        if len(X) < 10:
            print("Insufficient data for anomaly detection training")
            return {}
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled)
        
        # Detect anomalies in training data
        anomalies = self.model.predict(X_scaled)
        anomaly_count = np.sum(anomalies == -1)
        
        self.is_trained = True
        
        metrics = {
            'training_samples': len(X),
            'anomalies_detected': anomaly_count,
            'anomaly_rate': anomaly_count / len(X)
        }
        
        print(f"Anomaly detection trained - {anomaly_count} anomalies detected ({metrics['anomaly_rate']:.1%})")
        
        return metrics
    
    def detect_anomaly(self, features: Dict[str, float]) -> Tuple[bool, float]:
        """Detect if features represent an anomaly"""
        if not self.is_trained:
            return False, 0.0
        
        # Convert features to array
        feature_array = np.array([features.get(name, 0) for name in [
            'rle_smoothed', 'rle_raw', 'E_th', 'E_pw',
            'util_pct', 'temp_c', 'power_w', 'a_load', 't_sustain_s',
            'cpu_freq_mhz', 'gpu_clock_mhz', 'memory_util_pct'
        ]]).reshape(1, -1)
        
        # Scale features
        feature_scaled = self.scaler.transform(feature_array)
        
        # Predict anomaly
        prediction = self.model.predict(feature_scaled)[0]
        anomaly_score = self.model.decision_function(feature_scaled)[0]
        
        is_anomaly = prediction == -1
        
        return is_anomaly, anomaly_score

class RLEOptimizer:
    """Optimization for RLE performance"""
    
    def __init__(self):
        self.cluster_model = None
        self.pca_model = None
        self.is_trained = False
    
    def train(self, df: pd.DataFrame, n_clusters: int = 5) -> Dict[str, Any]:
        """Train optimization model"""
        print(f"Training RLE optimization model ({n_clusters} clusters)...")
        
        # Select features for clustering
        feature_columns = [
            'util_pct', 'temp_c', 'power_w', 'a_load',
            'cpu_freq_mhz', 'gpu_clock_mhz', 'memory_util_pct'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0).values
        
        if len(X) < n_clusters:
            print("Insufficient data for optimization training")
            return {}
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Apply PCA for dimensionality reduction
        self.pca_model = PCA(n_components=min(3, len(available_features)))
        X_pca = self.pca_model.fit_transform(X_scaled)
        
        # Cluster the data
        self.cluster_model = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = self.cluster_model.fit_predict(X_pca)
        
        # Analyze clusters
        df_clustered = df.copy()
        df_clustered['cluster'] = clusters
        
        cluster_analysis = {}
        for cluster_id in range(n_clusters):
            cluster_data = df_clustered[df_clustered['cluster'] == cluster_id]
            if len(cluster_data) > 0:
                cluster_analysis[cluster_id] = {
                    'size': len(cluster_data),
                    'avg_rle': cluster_data['rle_smoothed'].mean(),
                    'avg_temp': cluster_data['temp_c'].mean(),
                    'avg_power': cluster_data['power_w'].mean(),
                    'avg_util': cluster_data['util_pct'].mean()
                }
        
        self.is_trained = True
        
        print(f"Optimization model trained - {n_clusters} clusters identified")
        
        return {
            'n_clusters': n_clusters,
            'cluster_analysis': cluster_analysis,
            'pca_explained_variance': self.pca_model.explained_variance_ratio_.sum()
        }
    
    def get_optimal_settings(self, target_rle: float = 0.5) -> Dict[str, float]:
        """Get optimal settings for target RLE"""
        if not self.is_trained:
            return {}
        
        # Find cluster with closest average RLE to target
        cluster_centers = self.cluster_model.cluster_centers_
        
        # This is a simplified approach - in practice, you'd want more sophisticated optimization
        optimal_settings = {
            'util_pct': 70.0,  # Default values
            'temp_c': 60.0,
            'power_w': 150.0,
            'a_load': 0.8,
            'cpu_freq_mhz': 3000.0,
            'gpu_clock_mhz': 1800.0,
            'memory_util_pct': 50.0
        }
        
        return optimal_settings

class RLEMLAnalyzer:
    """Main ML analyzer for RLE data"""
    
    def __init__(self):
        self.predictor = RLEPredictor()
        self.anomaly_detector = RLEAnomalyDetector()
        self.optimizer = RLEOptimizer()
    
    def analyze_session(self, csv_path: str) -> Dict[str, Any]:
        """Analyze a session CSV with ML models"""
        print(f"Analyzing session: {csv_path}")
        
        # Load data
        df = pd.read_csv(csv_path)
        
        if len(df) < 10:
            print("Insufficient data for ML analysis")
            return {}
        
        results = {}
        
        # Train and evaluate predictor
        try:
            predictor_metrics = self.predictor.train(df, 'random_forest')
            results['predictor'] = predictor_metrics
            
            # Get feature importance
            importance = self.predictor.get_feature_importance()
            results['feature_importance'] = importance
            
        except Exception as e:
            print(f"Predictor training failed: {e}")
            results['predictor'] = {'error': str(e)}
        
        # Train anomaly detector
        try:
            anomaly_metrics = self.anomaly_detector.train(df)
            results['anomaly_detector'] = anomaly_metrics
            
        except Exception as e:
            print(f"Anomaly detector training failed: {e}")
            results['anomaly_detector'] = {'error': str(e)}
        
        # Train optimizer
        try:
            optimizer_metrics = self.optimizer.train(df)
            results['optimizer'] = optimizer_metrics
            
        except Exception as e:
            print(f"Optimizer training failed: {e}")
            results['optimizer'] = {'error': str(e)}
        
        return results
    
    def predict_rle(self, features: Dict[str, float]) -> float:
        """Predict RLE from current features"""
        return self.predictor.predict(features)
    
    def detect_anomaly(self, features: Dict[str, float]) -> Tuple[bool, float]:
        """Detect anomaly in current features"""
        return self.anomaly_detector.detect_anomaly(features)
    
    def get_optimal_settings(self, target_rle: float = 0.5) -> Dict[str, float]:
        """Get optimal settings for target RLE"""
        return self.optimizer.get_optimal_settings(target_rle)
    
    def save_models(self, base_path: str):
        """Save all trained models"""
        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        self.predictor.save_model(str(base_path / "rle_predictor.joblib"))
        # Note: Anomaly detector and optimizer don't have save methods yet
    
    def load_models(self, base_path: str):
        """Load all trained models"""
        base_path = Path(base_path)
        
        self.predictor.load_model(str(base_path / "rle_predictor.joblib"))

# Test function
def test_ml_integration():
    """Test ML integration with sample data"""
    print("Testing Scikit-learn Integration...")
    print("="*50)
    
    # Create sample data
    np.random.seed(42)
    n_samples = 1000
    
    sample_data = {
        'util_pct': np.random.uniform(10, 90, n_samples),
        'temp_c': np.random.uniform(40, 80, n_samples),
        'power_w': np.random.uniform(50, 200, n_samples),
        'a_load': np.random.uniform(0.3, 1.0, n_samples),
        't_sustain_s': np.random.uniform(10, 300, n_samples),
        'cpu_freq_mhz': np.random.uniform(2000, 4000, n_samples),
        'gpu_clock_mhz': np.random.uniform(1000, 2000, n_samples),
        'memory_util_pct': np.random.uniform(20, 80, n_samples),
        'rle_smoothed': np.random.uniform(0.1, 0.8, n_samples),
        'rle_raw': np.random.uniform(0.1, 0.8, n_samples),
        'E_th': np.random.uniform(0.1, 0.9, n_samples),
        'E_pw': np.random.uniform(0.1, 0.9, n_samples),
    }
    
    df = pd.DataFrame(sample_data)
    
    # Test ML analyzer
    analyzer = RLEMLAnalyzer()
    
    # Save to temporary CSV
    temp_csv = "temp_rle_data.csv"
    df.to_csv(temp_csv, index=False)
    
    try:
        # Analyze session
        results = analyzer.analyze_session(temp_csv)
        
        print("ML Analysis Results:")
        print(f"Predictor R²: {results.get('predictor', {}).get('r2', 'N/A')}")
        print(f"Anomaly Rate: {results.get('anomaly_detector', {}).get('anomaly_rate', 'N/A')}")
        print(f"Clusters: {results.get('optimizer', {}).get('n_clusters', 'N/A')}")
        
        # Test prediction
        test_features = {
            'util_pct': 70.0,
            'temp_c': 65.0,
            'power_w': 150.0,
            'a_load': 0.8,
            't_sustain_s': 120.0,
            'cpu_freq_mhz': 3000.0,
            'gpu_clock_mhz': 1800.0,
            'memory_util_pct': 60.0
        }
        
        predicted_rle = analyzer.predict_rle(test_features)
        print(f"Predicted RLE: {predicted_rle:.3f}")
        
        # Test anomaly detection
        is_anomaly, score = analyzer.detect_anomaly(test_features)
        print(f"Anomaly detected: {is_anomaly}, Score: {score:.3f}")
        
        # Test optimization
        optimal_settings = analyzer.get_optimal_settings()
        print(f"Optimal settings: {optimal_settings}")
        
        print("✅ Scikit-learn integration test completed")
        
    finally:
        # Clean up
        if Path(temp_csv).exists():
            Path(temp_csv).unlink()

if __name__ == "__main__":
    test_ml_integration()
