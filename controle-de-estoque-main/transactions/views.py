from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    View, 
    ListView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.db import transaction
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import (
    PurchaseBill, 
    Supplier, 
    PurchaseItem,
    PurchaseBillDetails,
    SaleBill,  
    SaleItem,
    SaleBillDetails
)
from .forms import (
    SelectSupplierForm,
    PurchaseItemForm,
    PurchaseItemFormset,
    PurchaseDetailsForm, 
    SupplierForm, 
    SaleForm,
    SaleItemFormset,
    SaleDetailsForm
)
from inventory.models import Stock

class SupplierListView(ListView):
    model = Supplier
    template_name = "suppliers/suppliers_list.html"
    queryset = Supplier.objects.filter(is_deleted=False)
    paginate_by = 10

class SupplierCreateView(SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    success_url = '/transactions/suppliers'
    success_message = "O fornecedor foi criado com sucesso"
    template_name = "suppliers/edit_supplier.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = 'Novo fornecedor'
        context["savebtn"] = 'Adicionar fornecedor'
        return context     

class SupplierUpdateView(SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    success_url = '/transactions/suppliers'
    success_message = "O fornecedor foi atualizado com sucesso"
    template_name = "suppliers/edit_supplier.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = 'Editar fornecedor'
        context["savebtn"] = 'Salvar alterações'
        context["delbtn"] = 'Deletar fornecedor'
        return context

class SupplierDeleteView(View):
    template_name = "suppliers/delete_supplier.html"
    success_message = "Fornecedor deletado com sucesso"

    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        return render(request, self.template_name, {'object' : supplier})

    def post(self, request, pk):  
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.is_deleted = True
        supplier.save()                                               
        messages.success(request, self.success_message)
        return redirect('suppliers-list')

class SupplierView(View):
    def get(self, request, name):
        supplierobj = get_object_or_404(Supplier, name=name)
        bill_list = PurchaseBill.objects.filter(supplier=supplierobj)
        page = request.GET.get('page', 1)
        paginator = Paginator(bill_list, 10)
        try:
            bills = paginator.page(page)
        except PageNotAnInteger:
            bills = paginator.page(1)
        except EmptyPage:
            bills = paginator.page(paginator.num_pages)
        context = {
            'supplier'  : supplierobj,
            'bills'     : bills
        }
        return render(request, 'suppliers/supplier.html', context)

class PurchaseView(ListView):
    model = PurchaseBill
    template_name = "purchases/purchases_list.html"
    context_object_name = 'bills'
    ordering = ['-time']
    paginate_by = 10

class SelectSupplierView(View):
    form_class = SelectSupplierForm
    template_name = 'purchases/select_supplier.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            supplierid = request.POST.get("supplier")
            supplier = get_object_or_404(Supplier, id=supplierid)
            return redirect('new-purchase', supplier.pk)
        return render(request, self.template_name, {'form': form})

class PurchaseCreateView(View):                                                 
    template_name = 'purchases/new_purchase.html'

    def get(self, request, pk):
        form = PurchaseItemForm(request.GET or None)
        formset = PurchaseItemFormset(request.GET or None)
        supplierobj = get_object_or_404(Supplier, pk=pk)
        context = {
            'form'      : form,
            'formset'   : formset,
            'supplier'  : supplierobj,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        supplierobj = get_object_or_404(Supplier, pk=pk)
        form = PurchaseItemForm(request.POST)
        formset = PurchaseItemFormset(request.POST)
        if formset.is_valid() and form.is_valid():
            try:
                billobj = form.save(commit=False)
                billobj.supplier = supplierobj
                billobj.save()

            except Exception as exc:
                print('Exception error!! ',exc)
                context = {
                    'form'      : form,
                    'formset'   : formset,
                }
                return render(request, self.template_name, context)
            
            try:
                billdetailsobj = PurchaseDetailsForm(billno=billobj)
                billdetailsobj.save()

            except Exception as exc:
                print('Exception error! ',exc)
                billobj.delete()
                context = {
                    'form'      : form,
                    'formset'   : formset,
                }
                return render(request, self.template_name, context)

            for form in formset:
                billitem = form.save(commit=False)
                billitem.billno = billobj
                stock = get_object_or_404(Stock, name=billitem.stock.name)
                billitem.totalprice = billitem.perprice * billitem.quantity
                stock.quantity += billitem.quantity
                billdetailsobj.total += billitem.totalprice
                stock.save()
                billitem.save()

            billdetailsobj.save()
            messages.success(request, "Purchased items have been registered successfully")
            return redirect('purchase-bill', billno=billobj.billno)
        form = PurchaseItemForm(request.GET or None)
        formset = PurchaseItemFormset(request.GET or None)
        context = {
            'form'      : form,
            'formset'   : formset,
        }
        return render(request, self.template_name, context)
        

        # def post(self, request, pk):
        #     form = PurchaseItemForm(request.POST)
        #     formset = PurchaseItemFormset(request.POST)
        #     supplierobj = get_object_or_404(Supplier, pk=pk)
        #     if formset.is_valid() and form.is_valid():
        #         try:
        #             billobj = form.save(commit=False)
        #             billobj.save()

        #         except Exception as exc:
        #             print('Exception error!! ',exc)
        #             context = {
        #                 'form'      : form,
        #                 'formset'   : formset,
        #             }
        #             return render(request, self.template_name, context)
                
        #         try:
        #             billdetailsobj = PurchaseDetailsForm(billno=billobj)
        #             billdetailsobj.save()

        #         except Exception as exc:
        #             print('Exception error! ',exc)
        #             billobj.delete()
        #             context = {
        #                 'form'      : form,
        #                 'formset'   : formset,
        #             }
        #             return render(request, self.template_name, context)

        #         for form in formset:
        #             billitem = form.save(commit=False)
        #             billitem.billno = billobj
        #             stock = get_object_or_404(Stock, name=billitem.stock.name)
        #             billitem.totalprice = billitem.perprice * billitem.quantity
        #             stock.quantity += billitem.quantity
        #             billdetailsobj.total += billitem.totalprice
        #             stock.save()
        #             billitem.save()

        #         billdetailsobj.save()
        #         messages.success(request, "Purchased items have been registered successfully")
        #         return redirect('purchase-bill', billno=billobj.billno)
        #     form = PurchaseItemForm(request.GET or None)
        #     formset = PurchaseItemFormset(request.GET or None)
        #     context = {
        #         'form'      : form,
        #         'formset'   : formset,
        #     }
        #     return render(request, self.template_name, context)

    

class PurchaseDeleteView(SuccessMessageMixin, DeleteView):
    model = PurchaseBill
    template_name = "purchases/delete_purchase.html"
    success_url = '/transactions/purchases'
    
    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        items = PurchaseItem.objects.filter(billno=self.object.billno)
        for item in items:
            stock = get_object_or_404(Stock, name=item.stock.name)
            if stock.is_deleted == False:
                stock.quantity -= item.quantity
                stock.save()
        messages.success(self.request, "A fatura da compra foi deletada com sucesso")
        return super(PurchaseDeleteView, self).delete(*args, **kwargs)

class SaleView(ListView):
    model = SaleBill
    template_name = "sales/sales_list.html"
    context_object_name = 'bills'
    ordering = ['-time']
    paginate_by = 10

class SaleCreateView(View):                                                      
    template_name = 'sales/new_sale.html'

    def get(self, request):
        form = SaleForm(request.GET or None)
        formset = SaleItemFormset(request.GET or None)
        stocks = Stock.objects.filter(is_deleted=False)
        context = {
            'form'      : form,
            'formset'   : formset,
            'stocks'    : stocks
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = SaleForm(request.POST)
        formset = SaleItemFormset(request.POST)
        if form.is_valid() and formset.is_valid():
            try:
                billobj = form.save(commit=False)
                billobj.save()

            except Exception as exc:
                print('Exception error! ',exc)
                context = {
                    'form'      : form,
                    'formset'   : formset,
                }
                return render(request, self.template_name, context)
            
            try:
                billdetailsobj = SaleBillDetails(billno=billobj)
                billdetailsobj.save()

            except Exception as exc:
                print('Exception error! ',exc)
                billobj.delete()
                context = {
                    'form'      : form,
                    'formset'   : formset,
                }
                return render(request, self.template_name, context)

            for form in formset:
                billitem = form.save(commit=False)
                billitem.billno = billobj
                stock = get_object_or_404(Stock, name=billitem.stock.name)      
                billitem.totalprice = billitem.perprice * billitem.quantity
                stock.quantity -= billitem.quantity
                billdetailsobj.total += billitem.totalprice 
                stock.save()
                billitem.save()

            billdetailsobj.save()
            messages.success(request, "Itens vendidos registrados com sucesso")
            return redirect('sale-bill', billno=billobj.billno)
        form = SaleForm(request.GET or None)
        formset = SaleItemFormset(request.GET or None)
        context = {
            'form'      : form,
            'formset'   : formset,
        }
        return render(request, self.template_name, context)

class SaleDeleteView(SuccessMessageMixin, DeleteView):
    model = SaleBill
    template_name = "sales/delete_sale.html"
    success_url = '/transactions/sales'
    
    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        items = SaleItem.objects.filter(billno=self.object.billno)
        for item in items:
            stock = get_object_or_404(Stock, name=item.stock.name)
            if stock.is_deleted == False:
                stock.quantity += item.quantity
                stock.save()
        messages.success(self.request, "A fatura da venda foi deletada com sucesso")
        return super(SaleDeleteView, self).delete(*args, **kwargs)

class PurchaseBillView(View):
    model = PurchaseBill
    template_name = "bill/purchase_bill.html"
    bill_base = "bill/bill_base.html"

    def get(self, request, billno):
        context = {
            'bill'          : PurchaseBill.objects.get(billno=billno),
            'items'         : PurchaseItem.objects.filter(billno=billno),
            'billdetails'   : PurchaseBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)

    def post(self, request, billno):
        form = PurchaseDetailsForm(request.POST)
        if form.is_valid():
            billdetailsobj = PurchaseBillDetails.objects.get(billno=billno)
            billdetailsobj.total = request.POST.get("total")
            billdetailsobj.save()
            messages.success(request, "Os detalhes da fatura foram modificados com sucesso")
        context = {
            'bill'          : PurchaseBill.objects.get(billno=billno),
            'items'         : PurchaseItem.objects.filter(billno=billno),
            'billdetails'   : PurchaseBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)

class SaleBillView(View):
    model = SaleBill
    template_name = "bill/sale_bill.html"
    bill_base = "bill/bill_base.html"
    
    def get(self, request, billno):
        context = {
            'bill'          : SaleBill.objects.get(billno=billno),
            'items'         : SaleItem.objects.filter(billno=billno),
            'billdetails'   : SaleBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)

    def post(self, request, billno):
        form = SaleDetailsForm(request.POST)
        if form.is_valid():
            billdetailsobj = SaleBillDetails.objects.get(billno=billno)
            billdetailsobj.total = request.POST.get("total")
            billdetailsobj.save()
            messages.success(request, "Os detalhes da fatura foram modificados com sucesso")
        context = {
            'bill'          : SaleBill.objects.get(billno=billno),
            'items'         : SaleItem.objects.filter(billno=billno),
            'billdetails'   : SaleBillDetails.objects.get(billno=billno),
            'bill_base'     : self.bill_base,
        }
        return render(request, self.template_name, context)