
  class Data extends React.Component {
    constructor(props){
      super(props);
      this.state = {
        data: null,
        loading: true,
        error: null,
      };
    }

    componentDidMount(){
      const urlEndpoint = window.location.origin + '/anexos-upload-dashboard/'
      fetch(urlEndpoint, {
        method: 'GET',
        headers: {
          Accept: 'application/json'
        }
      }).then((response) => {
        return response.json();
      }).then((data) => {
        this.setState({ data, loading: false});
      })
      .catch((error) => {
        this.setState({ error, loading: false});
      });
    }

    render(){
      const { data, loading, error } = this.state;
      if (loading) return (<p className="h2">Cargando ...</p>);
      if (error) return (<p className="h2">ERROR: {error.message}</p>);

      return (
        <>
        {React.Children.map(this.props.children, (child) => React.cloneElement(child, {data}))}
        </>
      );
    }

  }

  class TableItemAnexos extends React.Component{
    constructor(props){
      super(props);
      this.state = { data: props.data , showModal: null};
    }

    handleShow = (key) => {
      this.setState({ showModal: key });
    }

    handleClose = () => {
      this.setState({ showModal: null });
    }

    render(){
      const listItem = this.state.data.map((i, index) => {
        return (
          <tr key={i.key__key || index}>
            <th scope="row"> { i.key__key }</th>
            <td>{ i.key__anexo }</td>
            <td>{ i.duration_hrs }</td>
            <td>{ formatDateTime(i.registro) }</td>
            <td>
              <button type="button" className="btn btn-outline-primary" onClick={ () => this.handleShow(i.key__key) } >
                VER {i.key__key} 
              </button>

              { this.state.showModal === i.key__key && (<DialogAnexo anexo={i.key__key} duration_hrs={i.duration_hrs} onClose={ this.handleClose }/>)}
            </td>
          </tr>
        );
      });
      return (
        <tbody>
          { listItem }
        </tbody>
      );
    }
  }
  
  class TableAnexos extends React.Component {

    render(){
      const {data} = this.props;
      if (!data || data.length === 0) {
        return <p>No hay datos disponibles</p>;
      }
      return (
          <>
        <table className="table table-hover table-sm" id="sortableTable">
        <thead className="table-info">
          <tr>
            <th scope="col">Key</th>
            <th scope="col">Anexo</th>
            <th scope="col">Duración de Caída</th>
            <th scope="col">Registro</th>
            <th scope="col">Detalles</th>
          </tr>
        </thead>
          <TableItemAnexos data={data}/>
      </table>
          </>
      );
    }
    
  }

  class Info extends React.Component {

    render(){
      const {data} = this.props;
      if (!data || data.length === 0) {
        return <p>No hay datos disponibles</p>;
      }
      
      return (
        <>
        <div className="row">
          <div className="col-6">
            <div className="card border-success mb-3"  style={{ width: "300px", height: "150px"}}>
              <div className="card-header text-success">Anexos en UP inicialmente</div>
              <div className="card-body text-success">
                <CountAll all={ data.data.count } />
              </div>
            </div>
          </div>
          <div className="col-6">
            <div className="card text-white bg-warning mb-3" style={{ width: "300px", height: "150px"}}>
              <div className="card-header">Resumen de Anexos Actualmente</div>
              <div className="card-body">
                <UpAndDown up={ data.data.up } up_rate={ data.data.up_rate } down={ data.data.down } down_rate={ data.data.down_rate }/>
              </div>
            </div>
          </div>
        </div>

        <div className="row">
          <div className="col-12">
            <div>
              <TableAnexos data={data.data.data}/>
            </div>
          </div>
        </div>
        </>
      );
    }
  }

  class UpAndDown extends React.Component {

    constructor(props){
      super(props);
      this.state = {up: props.up, up_rate: props.up_rate, down: props.down, down_rate: props.down_rate};
    }

    render(){
      return (
        <>
        <p className="h4" style={{ textAlign: "left" }}><strong>UP</strong>: { this.state.up } -- { this.state.up_rate } %</p>
        <p className="h4" style={{ textAlign: "left" }}><strong>DOWN</strong>: { this.state.down } -- {this.state.down_rate }%</p>
        </>
      );
    }
  }

  function formatDateTime(dateTimeString) {
    const date = new Date(dateTimeString);
    return date.toLocaleString('es-ES', {  
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      //second: '2-digit',
      //timeZoneName: 'short'
    });
  }

  class CountAll extends React.Component {

    constructor(props){
      super(props);
      this.state = { all: props.all};
    }

    render(){
      return (
        <>
        <p className="h1" style={{ textAlign: "center"}}><strong>TOTAL</strong>: { this.state.all }</p>
        </>
      );
    }
  }

  
  class DialogAnexo extends React.Component {
    constructor(props){
      super(props);
      this.state = { anexo: props.anexo, duration_hrs: props.duration_hrs };
    }

    render(){
      console.log(this.state.anexo)
      return (
        <div className={`modal fade ${this.props.isOpen ? 'show' : ''}`} style={{ display: this.props.isOpen ? 'block' : 'none' }} tabIndex="-1" role="dialog">
          <div className="modal-dialog" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title"> Anexo {this.state.anexo} </h5>
              </div>
              <div className="modal-body">
                <p>Duración de caída: {this.state.duration_hrs}</p>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secundary" data-bs-dismiss="modal">Close</button>
              </div>
            </div>
          </div>
        </div>
      );
    }
  }


  const domCountAllContainer = document.querySelector("#info");
  const rootCountAllContainer = ReactDOM.createRoot(domCountAllContainer);
  rootCountAllContainer.render(
    <Data>
      <Info />
    </Data>
  );

