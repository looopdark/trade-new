async function  check (){
    try{
        for(let i=0;i<123;i++){
            const response = await fetch('https://cryptonews-api.com/api/v1?tickers=BTC&items=3&page=1&token=r1s7l9nsmwxwy9qmygqfahr3ajcjhh0eqc1xfqfx')
            const data = response.json()
            console.log(data)
        }

    }catch(e){
        console.log(e)
    }
}
check()