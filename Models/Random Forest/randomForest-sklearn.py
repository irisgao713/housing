from sklearn.feature_extraction import text
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import sklearn.metrics as metrics
import pandas as pd
import numpy as np
import scipy.sparse as sp
import matplotlib.pyplot as plt
import os
import config

# -------------------------- Helper Functions ------------------------------
# Missing value imputation
# Input: Dataframe df, value to replace missing values with, column name
def missingImputation(df, value, colName):
    df[colName].fillna(value, inplace=True)

# Missing value imputation for multiple columns at once
def missingImputationMulti (df, value, colNames):
    for col in colNames:
        missingImputation(df, value, col)

# Create column with 3 categories based on the 10 category classification
# Input: DataFrame with column "Category" containing the 10 category classification
def threeCategory(df):
    df['Category_3'] = df['Category'].dropna().apply(lambda x: "1" if x < 3.0 else ("2" if x < 4.0 else "3"))
    df['Category_text'] = df['Category'].apply(lambda x: str(x))

# Fit the model and print the accuracy scores
def getResults(model_name, clf, test, train_x, train_y, test_x, test_y, proba=False):
    clf.fit(train_x, train_y)
    predict2 = clf.predict(test_x)
    test['predict2'] = predict2
    if proba:
        getClassificationProbability(model_name, clf, test, test_x)
    print(model_name)
    print("Prediction accuracy: %0.2f" % clf.score(test_x, test_y))
    print("OOB score: %0.2f" % clf.oob_score_)
    return test

# Gets the probability of the classification categories, output csv
def getClassificationProbability(model_name, clf, test, test_x):
    proba = pd.DataFrame(clf.predict_proba(test_x))
    proba = proba.add_prefix('proba_')
    test2 = test.reset_index()
    outfile = pd.concat([test2, proba], axis=1)
    outfile.to_csv(os.path.join(config.ROOT_DIR, "Categorization ML Data", "Outputs", f"{model_name}.csv"), index=False)

# -------------------------- Script to run and print the classifiers ------------------------------

# define input file path here:
# f = "../results/Standardized_Deduped_Datasets/1000samples_20180815_withoutstar_labelledJA.csv"
# f = "../results/Standardized_Deduped_Datasets/1000samples_20180815_labelledJA.csv"
f = os.path.join(config.ROOT_DIR, 'results', 'Standardized_Deduped_Datasets', "Imputated_data_sqft_price_rooms.csv")
f2= os.path.join(config.ROOT_DIR, 'results', 'Standardized_Deduped_Datasets',
                 'Imputated_data_Aggregated_Clean_20180815_clipped_no_loc.csv')

arr = []
arr2= []

df = pd.read_csv(f)
colNames = ['lat', 'long', 'price', 'sqft', 'rooms' ]
colNamesString = ['title', 'description']
df = df[pd.notnull(df['Category'])]
# Missing value imputation + collapse categories into 3
missingImputationMulti(df, -1, colNames)
missingImputationMulti(df, "", colNamesString)
threeCategory(df)

# One hot encoding for Rooms variable
rooms = pd.get_dummies(df['rooms'])
rooms = rooms.add_prefix('rms_')
df = pd.concat([df, rooms], axis=1)

# create a stratified train-test split
train, test = train_test_split(df, test_size=0.2, stratify=df['Category_3'])

# tfidf vectorizer for title
vec = text.TfidfVectorizer(max_df=0.7)
train_x = vec.fit_transform(train['title'])
test_x = vec.transform(test['title'])

# join the tf-idf matrix with other features
df2 = train[['rms_0.0', 'rms_0.1', 'rms_1.0', 'rms_2.0', 'rms_3.0', 'rms_4.0',
             'rms_5.0', 'rms_6.0', 'rms_7.0', 'rms_7.1', 'price', 'sqft']]
features = sp.hstack([train_x, df2.values])
test_features = sp.hstack([test_x, test[['rms_0.0', 'rms_0.1', 'rms_1.0', 'rms_2.0', 'rms_3.0', 'rms_4.0',
             'rms_5.0', 'rms_6.0', 'rms_7.0', 'rms_7.1', 'price', 'sqft']].values])

#Logistic regression with TFIDF on titles, 10 classes
model = LogisticRegression()
model.fit(train_x, train["Category_text"])
test['predict'] = model.predict(test_x)
scores = metrics.accuracy_score(test['Category_text'],test['predict'])
c_val_score = cross_val_score(model, train_x, train['Category_text'], cv=10)
print("Logistic Regression")
print("Accuracy: %0.2f (+/- %0.2f)" % (c_val_score.mean(), c_val_score.std() * 2))
print("Prediction: %0.2f" % scores)

# Random Forest Classifier from sklearn
clf = RandomForestClassifier(n_jobs=2, n_estimators=1000, random_state=1234, oob_score=True)

#Random forest, TFIDF titles, 10 classes
getResults("rf-titles-10categories", clf, test, train_x, train['Category_text'], test_x, test['Category_text'])

#Random forest, TFIDF titles, 3 classes
getResults("rf-titles-3categories", clf, test, train_x, train['Category_3'], test_x, test['Category_3'])

#Random forest, TFIDF titles + rooms, price, 10 classes
getResults("rf-titles-rms-price-10categories", clf, test, features, train['Category_text'],
           test_features, test['Category_text'])

#Random forest, TFIDF titles + rooms, price, 3 classes
getResults("rf-titles-rms-price-3categories", clf, test, features, train['Category_3'],
           test_features, test['Category_3'])

# To output the predictions on the test set, either set proba=True or:
# res = getResults....
# res.to_csv(filepath)

#arr.append(clf.score(test_features, test['Category_3']))
#arr2.append(1-clf.oob_score_)

#Code for doing a prediction on the imputed 3000+ data set.
# df_imputed=pd.read_csv(f2)
# df_imputed['title'].fillna("", inplace=True)
# whole=vec.transform(df_imputed['title'])
# imputed_rooms = df_imputed.get_dummies(df_imputed['rooms'])
# df_imputed = pd.concat([df_imputed, imputed_rooms], axis=1)
# df_imputed["Predicted"] = clf.predict(sp.hstack([whole, df_imputed[[0.0, 0.1, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 'price']].values]))
# df_imputed.to_csv("C:/Users/jocel/PycharmProjects/scraper/results/Standardized_Deduped_Datasets/Predicted_Aggregated_Clean_20180815_clipped_no_loc.csv")

#Code for OOB error plot
# arr=[]
# for i in range (1,2000):
#     clf = RandomForestClassifier(n_jobs=2, n_estimators=i, random_state=1234, oob_score=True)
#     clf.fit(features, train['Category_3'])
#     arr.append(1-clf.oob_score_)
#     print(i)
#
#
# x_coordinate = [i for i in range(len(arr))]
# plt.plot(x_coordinate, arr)
# plt.show()

# #Code for top influential features
# importances = clf.feature_importances_
# std = np.std([tree.feature_importances_ for tree in clf.estimators_],
#              axis=0)
# indices = np.argsort(importances)[::-1]
# print(importances.shape)
# print("Feature ranking:")
#
# for f in range(features.shape[1]):
#     print("%d. feature %d (%f)" % (f + 1, indices[f], importances[indices[f]]))

# # Code for plotting OOB and % accuracy
# x_coordinate = [i/20 for i in range(1, 20)]
# plt.plot(x_coordinate, arr, label="% Prediction accuracy")
# plt.plot(x_coordinate, arr2, label= "% OOB error")
# plt.title("Prediction accuracy and OOB error with varying max_df values")
# plt.xlabel("max_df")
# plt.show()