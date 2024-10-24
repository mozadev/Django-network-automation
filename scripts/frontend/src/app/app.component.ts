import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {

  hostname = window.location.hostname;
  message = `Hola desde Angular desde ${this.hostname}`;
  canEdit = true

  onEditClick(){
    this.canEdit = !this.canEdit;
    if (this.canEdit){
      this.message = "You can edit me";
    } else {
      this.message = "I'm read only!";
    }
  }
}
