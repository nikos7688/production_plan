from flask import Flask,request,jsonify

app = Flask(__name__)

@app.route('/productionplan', methods = ['GET','POST'])
def make_energy_plan():        
    data = request.get_json(force=True)
    load_all=data['load']
    wind=data['fuels']['wind(%)']/100
    
    efficiency_gas_big1=data['powerplants'][0]['efficiency']
    efficiency_gas_big2=data['powerplants'][1]['efficiency']
    efficiency_gas_small=data['powerplants'][2]['efficiency']
    efficiency_kerosine=data['powerplants'][3]['efficiency']

    price_co2=data['fuels']['co2(euro/ton)']
    price_gas=data['fuels']['gas(euro/MWh)']
    price_kerosine=data['fuels']['kerosine(euro/MWh)']

    cost_gas_big1=price_gas/efficiency_gas_big1+.3*price_co2
    cost_gas_big2=price_gas/efficiency_gas_big2+.3*price_co2
    cost_gas_small=price_gas/efficiency_gas_small+.3*price_co2
    cost_kerosine=price_kerosine/efficiency_kerosine
    #print the cost of production for every plant so as to decide the order of plant activation
    #print('The cost of 1MWh production from the 1st big gas-fired plant is:',round(cost_gas_big1,2))
    #print('The cost of 1MWh production from the 2nd big gas-fired plant is:',round(cost_gas_big2,2))
    #print('The cost of 1MWh production from the small gas-fired plant is:',round(cost_gas_small,2))
    #print('The cost of 1MWh production from the kerosine plant is:',round(cost_kerosine,2))

    pmax_gas_big1=data['powerplants'][0]['pmax']
    pmax_gas_big2=data['powerplants'][1]['pmax']
    pmax_gas_small=data['powerplants'][2]['pmax']
    pmax_kerosine=data['powerplants'][3]['pmax']
    pmax_windpark1=data['powerplants'][4]['pmax']
    pmax_windpark2=data['powerplants'][5]['pmax']

    pmin_gas_big1=data['powerplants'][0]['pmin']
    pmin_gas_big2=data['powerplants'][1]['pmin']
    pmin_gas_small=data['powerplants'][2]['pmin']

    p_gas_big1=p_gas_big2=p_gas_small=p_kerosine=p_windpark1=p_windpark2=0
    load_to_cover=load_all

#at the first stage we find the most cost-effective energy production plan
#firstly we activate the big windpark 
    if load_to_cover<=pmax_windpark1*wind:
        p_windpark1=round(load_to_cover/wind,1)
    else:
        if wind>0:
            p_windpark1=pmax_windpark1
        load_to_cover-=p_windpark1*wind

#secondly the small windpark
        if load_to_cover<=pmax_windpark2*wind:
            p_windpark2=round(load_to_cover/wind,1)
        else:
            if wind>0:
                p_windpark2=pmax_windpark2
            load_to_cover-=p_windpark2*wind

#then the first big gasfired power station
            if load_to_cover<=pmax_gas_big1*efficiency_gas_big1:
                p_gas_big1=round(load_to_cover/efficiency_gas_big1,1)
            else:
                p_gas_big1=pmax_gas_big1
                load_to_cover-=p_gas_big1*efficiency_gas_big1

#afterwards the second big gasfired power station
                if load_to_cover<=pmax_gas_big2*efficiency_gas_big2:
                    p_gas_big2=round(load_to_cover/efficiency_gas_big2,1)
                else:
                    p_gas_big2=pmax_gas_big2
                    load_to_cover-=p_gas_big2*efficiency_gas_big2

#we continue with the small gasfired power station
                    if load_to_cover<=pmax_gas_small*efficiency_gas_small:
                        p_gas_small=round(load_to_cover/efficiency_gas_small,1)
                    else:
                        p_gas_small=pmax_gas_small
                        load_to_cover-=p_gas_small*efficiency_gas_small

#and finally we bring into use the more expensive turbojet power station
                        if load_to_cover<=pmax_kerosine*efficiency_kerosine:
                            p_kerosine=round(load_to_cover/efficiency_kerosine,1)
                        else:
                            p_kerosine=pmax_kerosine
                            load_to_cover-=p_kerosine*efficiency_kerosine
                            print('We can not cover the demand. We need additional {0} MWh'.format(round(load_to_cover,2)))

#at the second stage we take care of cases where a gasfired powerplant needs to produce less than its pmin 
#either the big gasfired1 is substituted by the small gasfired or it produces some extra MWhs in the place of the big windpark  
    if p_gas_big1>0 and p_gas_big1<pmin_gas_big1:
        if p_gas_big1*efficiency_gas_big1>=pmin_gas_small*efficiency_gas_small and p_gas_big1*efficiency_gas_big1<=pmax_gas_small*efficiency_gas_small:
            p_gas_small=round(p_gas_big1*efficiency_gas_big1/efficiency_gas_small,1)
            p_gas_big1=0
        else:
            p_windpark1-=round((pmin_gas_big1-p_gas_big1)*efficiency_gas_big1/wind,1)
            p_gas_big1=pmin_gas_big1

#the extra MWhs the 2nd big gasfired produce are subtracted from the 1st big gasfired
    if p_gas_big2>0 and p_gas_big2<pmin_gas_big2:
        p_gas_big1-=round((pmin_gas_big2-p_gas_big2)*efficiency_gas_big2/efficiency_gas_big1,1)
        p_gas_big2=pmin_gas_big2

#the extra MEhs the small gasfired produces are subtracted from the 2nd big gasfired; please have in mind that
#the functioning of the small gasfired presupposes that the 2nd (and the 1st) big gasfired functions at full capacity
    if p_gas_small>0 and p_gas_small<pmin_gas_small:
        p_gas_big2-=round((pmin_gas_small-p_gas_small)*efficiency_gas_small/efficiency_gas_big2,1)
        p_gas_small=pmin_gas_small

    production_plan=[{'name':'windpark1', 'p':p_windpark1}, {'name':'windpark2', 'p':p_windpark2}, 
                     {'name':'gasfiredbig1', 'p':p_gas_big1}, {'name':'gasfiredbig2', 'p':p_gas_big2}, 
                     {'name':'gasfiredsmall', 'p':p_gas_small}, {'name':'turbojet', 'p':p_kerosine}]
    
    return jsonify(production_plan)

#verification that the sum of energy production is equal to the load 
#print(p_windpark1,p_windpark2,p_gas_big1,p_gas_big2,p_gas_small,p_kerosine)
#print((p_windpark1+p_windpark2)*wind+p_gas_big1*efficiency_gas_big1+p_gas_big2*efficiency_gas_big2+
#     p_gas_small*efficiency_gas_small+p_kerosine*efficiency_kerosine)

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=8888,debug=True)