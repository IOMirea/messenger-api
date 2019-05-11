
$(function() {
	var redirect = "{{ redirect|safe }}"
	var xhr = new XMLHttpRequest();
	xhr.onreadystatechange = function() {
		if (this.readyState !== XMLHttpRequest.DONE) {
			return
		}
		if (this.status == 400) {
			alert("Bad login or password")
		} else if (this.status === 401) {
			alert("Wrong login or password")
		} else if (this.status === 200) {
			window.location.assign(redirect)
		} else {
			alert("Something went terribly wrong. Please, try to refresh page or return back later")
		}
	}
	$("#auth_form").on("submit", function(e) {
		xhr.open("POST", window.location.href, true)
		xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
		xhr.send("login="+$("#login_field").val()+"&password="+$("#password_field").val())
	})
});
function ResetPassword() {
	var email = $("#login_field").val()
	if (email === "") {
		alert("Please, enter email")
		return
	}
	var xhr = new XMLHttpRequest();
	xhr.onreadystatechange = function() {
		if (this.readyState !== XMLHttpRequest.DONE) {
			return
		}
		if (this.status === 401) {
			alert('Invalid email')
		} else if (this.status === 200) {
			alert("Password restore link was sent to "+email+"\nYou have 12 hours to use it")
		} else {
			alert('Something went terribly wrong. Please, try to refresh page or return back later')
		}
	}
	xhr.open("POST", "{{ url('reset_password') }}", true)
	xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
	xhr.send("email="+email)
}
function showhide(){
	var x = document.getElementById("password_field");
	var y=document.getElementById("eye")
	if (x.type === "password") {
		x.type = "text";
		y.className="eyesl";
	} else {
		x.type = "password";
		y.className="eye";
	}
}
