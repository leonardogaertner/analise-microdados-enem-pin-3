from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

from database.operations import load_data

def main():

    df = load_data()

    #print(df["NU_NOTA_CH"].describe())
    #print(df["NU_NOTA_CH"].unique()[:20])

    #df, _ = preprocess_arvoreDecisao(dfBruto, categorizar_colunas=True)

    target_col = "NU_NOTA_CH"
    print(df[target_col].value_counts())

    X = df.drop(columns=[target_col])
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = DecisionTreeClassifier(max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred, zero_division=0))

if __name__ == "__main__":
    main()
    



