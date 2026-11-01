from train import parameters

def test_loss_changes_not_feature_budget():
    a=parameters('XGB_REG',101);b=parameters('XGB_CLASS',101);c=parameters('XGB_RANK',101)
    for k in ['n_estimators','max_depth','colsample_bytree','min_child_weight','reg_lambda','reg_alpha','subsample','learning_rate']:
        assert a[k]==b[k]==c[k]
    assert b['objective']=='binary:logistic'
    assert c['objective']=='rank:ndcg' and c['ndcg_exp_gain'] is False

def test_tree_classifier_uses_original_budget():
    a=parameters('ET_REG',211);b=parameters('ET_CLASS',211)
    assert a==b
    assert a['max_features']==.4 and a['n_estimators']==120 and a['random_state']==211
