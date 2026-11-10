"""Validation-calibrated out-of-distribution abstention helpers."""
from __future__ import annotations
import math


def _vector(value):
    result=tuple(float(item) for item in value)
    if not result or any(not math.isfinite(item) for item in result):
        raise ValueError('OOD vectors must be non-empty and finite')
    return result


def _distance(left,right):
    if len(left)!=len(right):
        raise ValueError('OOD vector dimensions do not match')
    return math.sqrt(sum((a-b)**2 for a,b in zip(left,right)))


def fit_ood_guard(training_vectors,validation_vectors,percentile=99.0):
    """Set the nearest-training-distance cutoff from validation examples only."""
    training=[_vector(row) for row in training_vectors]
    validation=[_vector(row) for row in validation_vectors]
    if not training or not validation:
        raise ValueError('OOD guard requires non-empty train and validation vectors')
    dimension=len(training[0])
    if any(len(row)!=dimension for row in training+validation):
        raise ValueError('OOD training and validation dimensions do not match')
    percentile=float(percentile)
    if not 0.0<percentile<=100.0:
        raise ValueError('percentile must be in (0, 100]')
    distances=sorted(min(_distance(row,reference) for reference in training) for row in validation)
    index=max(0,min(len(distances)-1,math.ceil(percentile/100.0*len(distances))-1))
    return {'threshold':distances[index],'percentile':percentile,'dimension':dimension,
            'training_count':len(training),'validation_count':len(validation),
            'method':'nearest_train_euclidean_validation_percentile'}


def is_out_of_distribution(vector,training_vectors,guard):
    """Abstain when a query is farther from every training row than validation allows."""
    query=_vector(vector); training=[_vector(row) for row in training_vectors]
    if not training:
        return True
    if len(query)!=int(guard['dimension']) or any(len(row)!=len(query) for row in training):
        return True
    nearest=min(_distance(query,row) for row in training)
    return nearest>float(guard['threshold'])
